"""Fetch historical hourly PM2.5 and PM10 observations from OpenAQ API v3.

WP3 pilot and WP5 full observation history:
- Reads active stations with decision == 'use' from data/stations_candidates.csv
- Finds sensor IDs from raw OpenAQ location files in data/raw
- Partitions timeline into 35-day non-overlapping windows (aligned to UTC midnight)
- UNVERIFIED: OpenAQ docs do not specify if datetime_to is inclusive; 1-hour overlap
  is applied to prevent boundary data loss. Downstream parser deduplicates.
- Resumes incrementally skipping windows already in manifest with HTTP 200
- Enforces request cap, rate limiting (429 Retry-After), 5xx retry with backoff,
  disk guard (>= 3 GB), and plan confirmation (> 200 requests requires --yes).
- Saves raw responses atomically to
  data/raw/openaq/<station_id>/<sensor_id>/<fetch_time_utc>_p<page>.json
- Logs immutable audit records to data/raw/openaq/manifest.jsonl.
"""

from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta
from typing import Any

API_BASE = "https://api.openaq.org/v3"
USER_AGENT = "NCR-Hawa-ObservationPilot/0.1"
DEFAULT_DELAY_SEC = 1.1
DEFAULT_TIMEOUT_SEC = 15.0
DEFAULT_MAX_REQUESTS = 60
DEFAULT_HISTORY_CONFIG_PATH = "configs/openaq_history.json"
DEFAULT_MIN_DISK_GB = 3.0

DEFAULT_HISTORY_CONFIG: dict[str, Any] = {
    "from_date": "2024-01-01",
    "window_days": 35,
    "request_spacing": 1.1,
    "max_requests_per_run": 1200,
}

# Pilot stations approved for WP3 pilot
DEFAULT_PILOT_STATIONS: list[dict[str, Any]] = [
    {
        "station_id": 8118,
        "name": "New Delhi",
        "area": "central_delhi",
        "provider": "AirNow",
        "sensors": {"pm25": 23534, "pm10": None},
    },
    {
        "station_id": 6934,
        "name": "Dr. Karni Singh Shooting Range, Delhi - DPCC",
        "area": "faridabad",
        "provider": "CPCB",
        "sensors": {"pm25": 12235011, "pm10": 12235010},
    },
    {
        "station_id": 235,
        "name": "Anand Vihar, New Delhi - DPCC",
        "area": "ghaziabad",
        "provider": "CPCB",
        "sensors": {"pm25": 12235610, "pm10": 12235609},
    },
    {
        "station_id": 301,
        "name": "Vikas Sadan, Gurugram - HSPCB",
        "area": "gurugram",
        "provider": "CPCB",
        "sensors": {"pm25": 14258988, "pm10": 14258987},
    },
    {
        "station_id": 5598,
        "name": "Sector - 125, Noida, UP - UPPCB",
        "area": "noida",
        "provider": "CPCB",
        "sensors": {"pm25": 12235187, "pm10": 12235186},
    },
]


class RequestCapExceededError(Exception):
    """Raised when total HTTP requests reach the configured maximum cap."""


class ApiKeyRejectedError(Exception):
    """Raised when the OpenAQ API rejects the provided API key (HTTP 401)."""


class RequestTracker:
    """Tracks number of HTTP requests and enforces max request cap and timing."""

    def __init__(self, max_requests: int = DEFAULT_MAX_REQUESTS) -> None:
        self.max_requests = max_requests
        self.count = 0
        self.last_request_time: float | None = None
        self.last_status_code: int | None = None

    def record_request(self) -> None:
        """Increment count or raise error if cap is exceeded."""
        if self.count >= self.max_requests:
            raise RequestCapExceededError(
                f"Request cap of {self.max_requests} requests reached."
            )
        self.count += 1
        self.last_request_time = time.time()


def get_api_key() -> str:
    """Read API key from environment without printing or leaking secrets."""
    key = os.environ.get("OPENAQ_API_KEY", "").strip()
    if not key:
        print("Error: OPENAQ_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)
    return key


def normalize_iso_utc(date_str: str, is_end_of_day: bool = False) -> str:
    """Normalize date or datetime input to ISO-8601 UTC string.

    Accepts YYYY-MM-DD or full ISO strings. For YYYY-MM-DD, attaches T00:00:00Z
    (or T23:59:59Z if is_end_of_day is True).
    """
    clean = date_str.strip()
    if len(clean) == 10 and clean.count("-") == 2:
        if is_end_of_day:
            return f"{clean}T23:59:59Z"
        return f"{clean}T00:00:00Z"
    if clean.endswith("Z") or "+" in clean or "-" in clean[10:]:
        return clean
    return f"{clean}Z"


def parse_iso_utc_dt(ts: str | None) -> datetime | None:
    """Parse an ISO UTC timestamp into a timezone-aware UTC datetime."""
    if not ts or ts.lower() == "unknown":
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except Exception:
        return None


def build_hours_url(
    sensor_id: int,
    datetime_from: str,
    datetime_to: str,
    limit: int = 1000,
    page: int = 1,
) -> str:
    """Build query URL for /v3/sensors/{sensor_id}/hours."""
    params = {
        "datetime_from": datetime_from,
        "datetime_to": datetime_to,
        "limit": str(limit),
        "page": str(page),
    }
    query_str = urllib.parse.urlencode(params)
    return f"{API_BASE}/sensors/{sensor_id}/hours?{query_str}"


def validate_hours_payload(
    raw_bytes: bytes,
) -> tuple[dict[str, Any] | None, str | None]:
    """Validate that response bytes form valid JSON with expected meta and results.

    Returns (parsed_dict, error_message).
    """
    try:
        data = json.loads(raw_bytes.decode("utf-8"))
    except Exception as e:
        return None, f"invalid_json: {e}"

    if not isinstance(data, dict):
        return None, "response_not_a_json_object"

    if data.get("error"):
        reason = data.get("reason", "unknown_api_error")
        return None, f"api_error: {reason}"

    if "meta" not in data or not isinstance(data["meta"], dict):
        return None, "missing_or_invalid_meta"

    if "results" not in data or not isinstance(data["results"], list):
        return None, "missing_or_invalid_results"

    return data, None


def append_jsonl(filepath: str, entry: dict[str, Any]) -> None:
    """Append a JSON line to manifest or failure log."""
    parent = os.path.dirname(filepath)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")


def write_raw_file_atomically(target_path: str, raw_bytes: bytes) -> None:
    """Write raw response bytes to target path atomically via a temporary file."""
    if not isinstance(raw_bytes, (bytes, bytearray)):
        raise TypeError("raw_bytes must be a bytes-like object")

    parent = os.path.dirname(target_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    tmp_path = f"{target_path}.tmp"
    try:
        with open(tmp_path, "wb") as f:
            f.write(raw_bytes)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, target_path)
    except Exception:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        raise


def make_request_with_retry(
    url: str,
    api_key: str,
    tracker: RequestTracker,
    timeout: float = DEFAULT_TIMEOUT_SEC,
    delay_sec: float = DEFAULT_DELAY_SEC,
    max_retries: int = 3,
) -> tuple[int, bytes, dict[str, str]]:
    """Execute GET request with rate limiting delay, backoff, and auth header.

    Retries only 429 and 5xx errors.
    Returns (status_code, raw_bytes, response_headers).
    """
    headers = {
        "User-Agent": USER_AGENT,
        "X-API-Key": api_key,
        "Accept": "application/json",
    }
    req = urllib.request.Request(url, headers=headers)

    for attempt in range(max_retries + 1):
        tracker.record_request()
        if delay_sec > 0:
            time.sleep(delay_sec)

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                resp_headers = {k.lower(): v for k, v in resp.headers.items()}
                raw_bytes = resp.read()
                tracker.last_status_code = resp.status
                return resp.status, raw_bytes, resp_headers
        except urllib.error.HTTPError as e:
            tracker.last_status_code = e.code
            resp_headers = (
                {k.lower(): v for k, v in e.headers.items()} if e.headers else {}
            )
            if e.code == 401:
                print("API key rejected", file=sys.stderr)
                try:
                    err_bytes = e.read()
                except Exception:
                    err_bytes = b""
                return 401, err_bytes, resp_headers
            if e.code == 429 or e.code >= 500:
                if attempt < max_retries:
                    retry_after = resp_headers.get("retry-after") or resp_headers.get(
                        "x-ratelimit-reset"
                    )
                    try:
                        wait_sec = (
                            float(retry_after)
                            if retry_after
                            else (2.0 ** (attempt + 1))
                        )
                    except ValueError:
                        wait_sec = 2.0 ** (attempt + 1)
                    time.sleep(wait_sec)
                    continue
            try:
                err_bytes = e.read()
            except Exception:
                err_bytes = b""
            return e.code, err_bytes, resp_headers
        except urllib.error.URLError as e:
            if attempt < max_retries:
                time.sleep(2.0 ** (attempt + 1))
                continue
            raise e

    raise RuntimeError("Max retries exceeded.")


def load_history_config(
    config_path: str = DEFAULT_HISTORY_CONFIG_PATH,
) -> dict[str, Any]:
    """Load openaq history configuration or return defaults."""
    if os.path.exists(config_path):
        try:
            with open(config_path, encoding="utf-8") as f:
                data = json.load(f)
                return {**DEFAULT_HISTORY_CONFIG, **data}
        except Exception:
            return DEFAULT_HISTORY_CONFIG.copy()
    return DEFAULT_HISTORY_CONFIG.copy()


def load_sensor_map_from_raw(
    raw_locations_dir: str = "data/raw",
) -> dict[int, dict[str, int]]:
    """Scan raw location files and map station_id -> {param_name: sensor_id}."""
    patterns = [
        os.path.join(raw_locations_dir, "locations_*.json"),
        os.path.join(raw_locations_dir, "*.json"),
    ]
    files: list[str] = []
    for pat in patterns:
        files.extend(glob.glob(pat))

    sensor_map: dict[int, dict[str, int]] = {}
    for fpath in set(files):
        if "manifest" in fpath or "failures" in fpath or "licenses" in fpath:
            continue
        try:
            with open(fpath, encoding="utf-8") as fp:
                data = json.load(fp)
            results = data.get("results", [])
            for loc in results:
                sid = loc.get("id")
                if sid is None:
                    continue
                sensors = loc.get("sensors", [])
                s_dict: dict[str, int] = {}
                for s in sensors:
                    param_name = (s.get("parameter") or {}).get("name")
                    sensor_id = s.get("id")
                    if param_name and sensor_id is not None:
                        s_dict[param_name.strip().lower()] = int(sensor_id)
                if s_dict:
                    sensor_map.setdefault(int(sid), {}).update(s_dict)
        except Exception:
            continue

    return sensor_map


def check_disk_space(
    path: str, min_gb: float = DEFAULT_MIN_DISK_GB
) -> tuple[bool, float]:
    """Check free disk space in GB on the drive holding path.

    Returns (has_sufficient_space, free_gb).
    """
    check_path = path
    while check_path and not os.path.exists(check_path):
        parent = os.path.dirname(check_path)
        if parent == check_path:
            break
        check_path = parent

    if not check_path or not os.path.exists(check_path):
        check_path = "."

    try:
        usage = shutil.disk_usage(check_path)
        free_gb = usage.free / (1024**3)
        return free_gb >= min_gb, round(free_gb, 2)
    except Exception:
        return True, 999.0


def read_manifest_completed_requests(
    manifest_path: str,
) -> set[tuple[int, str, str, int]]:
    """Read manifest and return set of completed requests.

    Returns set of (sensor_id, datetime_from, datetime_to, page).
    Only entries with http_status == 200 are counted as completed.
    Gracefully handles old manifest lines that lacked explicit datetime_from/to fields
    by parsing query parameters from the url field if necessary.
    """
    completed: set[tuple[int, str, str, int]] = set()
    if not os.path.exists(manifest_path):
        return completed

    with open(manifest_path, encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if not line_str:
                continue
            try:
                entry = json.loads(line_str)
            except Exception:
                continue

            if entry.get("http_status") != 200:
                continue

            sensor_id = entry.get("sensor_id")
            if sensor_id is None:
                continue

            dt_from = entry.get("datetime_from")
            dt_to = entry.get("datetime_to")
            page = entry.get("page")

            # Fallback for older manifest entries: extract from url
            if dt_from is None or dt_to is None or page is None:
                url_str = entry.get("url", "")
                if url_str:
                    try:
                        parsed = urllib.parse.urlparse(url_str)
                        qs = urllib.parse.parse_qs(parsed.query)
                        if dt_from is None:
                            dt_from = qs.get("datetime_from", [None])[0]
                        if dt_to is None:
                            dt_to = qs.get("datetime_to", [None])[0]
                        if page is None:
                            page_raw = qs.get("page", ["1"])[0]
                            page = int(page_raw)
                    except Exception:
                        pass

            if dt_from and dt_to and page is not None:
                try:
                    completed.add((int(sensor_id), str(dt_from), str(dt_to), int(page)))
                except (ValueError, TypeError):
                    pass

    return completed


def build_station_history_plan(
    stations_csv: str = "data/stations_candidates.csv",
    raw_locations_dir: str = "data/raw",
    parameters: list[str] | None = None,
    from_date: str = "2024-01-01",
    window_days: int = 35,
    now_utc: datetime | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build observation history window plan for stations with decision == 'use'.

    Returns (planned_windows, missing_sensors).
    """
    if parameters is None:
        parameters = ["pm25"]
    normalized_params = [p.strip().lower() for p in parameters if p.strip()]

    if now_utc is None:
        now_utc = datetime.now(UTC)

    # 1. Read use stations from candidates CSV
    use_stations: list[dict[str, Any]] = []
    if os.path.exists(stations_csv):
        with open(stations_csv, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("decision") == "use":
                    use_stations.append(row)

    use_stations.sort(key=lambda x: int(x.get("station_id", 0)))

    # 2. Build sensor map from raw location files
    sensor_map = load_sensor_map_from_raw(raw_locations_dir)

    # 3. Base time windows (aligned to UTC midnight, 35-day duration)
    # UNVERIFIED: OpenAQ docs do not specify whether datetime_to is inclusive.
    # We overlap windows by 1 hour (window_days * 24h + 1h) to prevent data loss.
    # Downstream parser (features/observations.py) deduplicates by sensor/time.
    start_dt = datetime.fromisoformat(from_date.replace("Z", "+00:00"))
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=UTC)
    else:
        start_dt = start_dt.astimezone(UTC)
    start_dt = datetime(
        start_dt.year, start_dt.month, start_dt.day, 0, 0, 0, tzinfo=UTC
    )

    raw_windows: list[tuple[datetime, datetime]] = []
    curr = start_dt
    while curr < now_utc:
        w_start = curr
        w_end = min(curr + timedelta(days=window_days, hours=1), now_utc)
        raw_windows.append((w_start, w_end))
        curr += timedelta(days=window_days)

    planned_windows: list[dict[str, Any]] = []
    missing_sensors: list[dict[str, Any]] = []

    for st in use_stations:
        sid = int(st["station_id"])
        sname = st.get("name", "Unknown")
        area = st.get("area_id", "unknown")
        dt_first = parse_iso_utc_dt(st.get("datetime_first"))
        dt_last = parse_iso_utc_dt(st.get("datetime_last"))

        st_sensors = sensor_map.get(sid, {})

        for param in normalized_params:
            sensor_id = st_sensors.get(param)
            if sensor_id is None:
                missing_sensors.append(
                    {
                        "station_id": sid,
                        "station_name": sname,
                        "area": area,
                        "parameter": param,
                        "reason": "no sensor id",
                    }
                )
                continue

            w_idx = 0
            for w_start, w_end in raw_windows:
                # Skip windows entirely before station's datetime_first
                if dt_first and w_end < dt_first:
                    continue
                # Skip windows entirely after station's datetime_last
                if dt_last and w_start > dt_last:
                    continue

                w_idx += 1
                planned_windows.append(
                    {
                        "station_id": sid,
                        "station_name": sname,
                        "area": area,
                        "parameter": param,
                        "sensor_id": sensor_id,
                        "datetime_from": w_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "datetime_to": w_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "window_index": w_idx,
                    }
                )

    return planned_windows, missing_sensors


def write_history_plan_report(
    planned_windows: list[dict[str, Any]],
    missing_sensors: list[dict[str, Any]],
    report_path: str = "reports/history_plan.md",
    config: dict[str, Any] | None = None,
    parameters: list[str] | None = None,
) -> str:
    """Generate reports/history_plan.md documenting the full history ingestion plan."""
    if config is None:
        config = DEFAULT_HISTORY_CONFIG
    if parameters is None:
        parameters = ["pm25"]

    distinct_stations = len({w["station_id"] for w in planned_windows})
    distinct_sensors = len({w["sensor_id"] for w in planned_windows})
    total_windows = len(planned_windows)
    est_minutes = (total_windows * float(config.get("request_spacing", 1.1))) / 60.0

    lines = [
        "# OpenAQ Observation History Plan (A-004)",
        "",
        "> **Notice**: This plan outlines historical hourly observation "
        "acquisition for Delhi-NCR stations.",
        "> **Note [Unverified]**: OpenAQ v3 documentation does not specify whether "
        "`datetime_to` is inclusive.",
        "> Windows are configured with a 1-hour overlap to prevent loss of "
        "boundary hourly readings.",
        "> Downstream processing (`features/observations.py`) safely deduplicates "
        "all identical timestamps.",
        "",
        "## 1. Plan Configuration Summary",
        "",
        f"- **From Date**: `{config.get('from_date', '2024-01-01')}` "
        "(aligned to Jan 2024 weather model coverage)",
        f"- **Target Parameters**: `{', '.join(parameters)}`",
        f"- **Window Size**: `{config.get('window_days', 35)}` days "
        "(up to 840 hours; fits within 1000-record page)",
        "- **Window Overlap**: 1 hour (`unverified` boundary inclusion)",
        f"- **Request Spacing**: `{config.get('request_spacing', 1.1)}` seconds "
        "(strict rate-limit adherence)",
        f"- **Max Requests per Run**: `{config.get('max_requests_per_run', 1200)}`",
        f"- **Active 'use' Stations Covered**: {distinct_stations}",
        f"- **Distinct Sensors Targeted**: {distinct_sensors}",
        f"- **Total Target Windows**: {total_windows}",
        f"- **Estimated Full Ingestion Duration**: ~{est_minutes:.1f} minutes",
        "",
        "## 2. Stations Lacking Requested Sensor IDs (Skipped)",
        "",
    ]

    if missing_sensors:
        lines.extend(
            [
                "| Station ID | Station Name | Area | Parameter | Status |",
                "|---|---|---|---|---|",
            ]
        )
        for m in missing_sensors:
            lines.append(
                f"| `{m['station_id']}` | {m['station_name']} | `{m['area']}` | "
                f"**{m['parameter']}** | *no sensor id* (skipped) |"
            )
    else:
        lines.append(
            "All targeted stations possess valid sensor IDs for the requested "
            "parameters."
        )

    lines.extend(
        [
            "",
            "## 3. Targeted Station Windows Summary",
            "",
            "| Station ID | Station Name | Area | Parameter | Sensor ID | "
            "Windows Planned |",
            "|---|---|---|---|---|---|",
        ]
    )

    by_sensor: dict[tuple[int, str, str, str, int], int] = {}
    for w in planned_windows:
        key = (
            w["station_id"],
            w["station_name"],
            w["area"],
            w["parameter"],
            w["sensor_id"],
        )
        by_sensor[key] = by_sensor.get(key, 0) + 1

    for (sid, sname, area, param, sensor_id), w_count in sorted(by_sensor.items()):
        lines.append(
            f"| `{sid}` | {sname} | `{area}` | **{param}** | `{sensor_id}` | "
            f"{w_count} |"
        )

    content = "\n".join(lines) + "\n"
    parent_dir = os.path.dirname(report_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(content)

    return content


def fetch_sensor_hours(
    station_id: int,
    sensor_id: int,
    parameter: str,
    datetime_from: str,
    datetime_to: str,
    api_key: str,
    raw_dir: str,
    tracker: RequestTracker,
    fetch_dt: datetime,
    limit: int = 1000,
    dry_run: bool = False,
    manifest_path: str | None = None,
    failures_path: str | None = None,
    completed_requests: set[tuple[int, str, str, int]] | None = None,
) -> tuple[int, int]:
    """Fetch all pages for a single sensor window and save atomically to archive.

    Returns (files_saved_count, failures_count).
    """
    if manifest_path is None:
        manifest_path = os.path.join(raw_dir, "manifest.jsonl")
    if failures_path is None:
        failures_path = os.path.join(raw_dir, "failures.jsonl")

    fetch_time_str = fetch_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    ts_slug = fetch_dt.strftime("%Y%m%dT%H%M%SZ")
    sensor_dir = os.path.join(raw_dir, str(station_id), str(sensor_id))

    page = 1
    files_saved = 0
    failures = 0

    while True:
        # Check manifest resume set before making request
        if (
            completed_requests
            and (sensor_id, datetime_from, datetime_to, page) in completed_requests
        ):
            print(
                f"Skipping completed window in manifest: station={station_id} "
                f"sensor={sensor_id} from={datetime_from} to={datetime_to} p={page}"
            )
            break

        target_filename = f"{ts_slug}_p{page}.json"
        target_path = os.path.join(sensor_dir, target_filename)
        normalized_file_path = target_path.replace("\\", "/")

        url = build_hours_url(
            sensor_id=sensor_id,
            datetime_from=datetime_from,
            datetime_to=datetime_to,
            limit=limit,
            page=page,
        )

        # Check file existence before making the request (never overwrite)
        if os.path.exists(target_path):
            print(f"Skipping existing file (idempotent): {normalized_file_path}")
            break

        if dry_run:
            print(
                f"[DRY-RUN] station={station_id} sensor={sensor_id} "
                f"param={parameter} page={page} -> {normalized_file_path}"
            )
            print(f"[DRY-RUN] URL: {url}")
            files_saved += 1
            break

        try:
            status_code, raw_bytes, resp_headers = make_request_with_retry(
                url=url,
                api_key=api_key,
                tracker=tracker,
            )
        except RequestCapExceededError as e:
            print(
                f"Warning: Request cap reached while fetching sensor {sensor_id}: {e}",
                file=sys.stderr,
            )
            append_jsonl(
                failures_path,
                {
                    "fetch_time_utc": fetch_time_str,
                    "station_id": station_id,
                    "sensor_id": sensor_id,
                    "parameter": parameter,
                    "url": url,
                    "http_status": None,
                    "error": "request_cap_exceeded",
                    "error_detail": str(e),
                },
            )
            failures += 1
            break
        except Exception as e:
            print(f"Error requesting sensor {sensor_id}: {e}", file=sys.stderr)
            append_jsonl(
                failures_path,
                {
                    "fetch_time_utc": fetch_time_str,
                    "station_id": station_id,
                    "sensor_id": sensor_id,
                    "parameter": parameter,
                    "url": url,
                    "http_status": None,
                    "error": "request_exception",
                    "error_detail": str(e),
                },
            )
            failures += 1
            break

        if status_code == 401:
            append_jsonl(
                failures_path,
                {
                    "fetch_time_utc": fetch_time_str,
                    "station_id": station_id,
                    "sensor_id": sensor_id,
                    "parameter": parameter,
                    "url": url,
                    "http_status": 401,
                    "error": "api_key_rejected",
                },
            )
            failures += 1
            break

        if status_code != 200:
            print(
                f"HTTP {status_code} error for sensor {sensor_id}",
                file=sys.stderr,
            )
            append_jsonl(
                failures_path,
                {
                    "fetch_time_utc": fetch_time_str,
                    "station_id": station_id,
                    "sensor_id": sensor_id,
                    "parameter": parameter,
                    "url": url,
                    "http_status": status_code,
                    "error": f"http_status_{status_code}",
                },
            )
            failures += 1
            break

        # Validate response payload
        parsed_data, val_err = validate_hours_payload(raw_bytes)
        if val_err or parsed_data is None:
            print(
                f"Validation error for sensor {sensor_id}: {val_err}",
                file=sys.stderr,
            )
            append_jsonl(
                failures_path,
                {
                    "fetch_time_utc": fetch_time_str,
                    "station_id": station_id,
                    "sensor_id": sensor_id,
                    "parameter": parameter,
                    "url": url,
                    "http_status": status_code,
                    "error": "validation_failed",
                    "error_detail": val_err,
                },
            )
            failures += 1
            break

        # Atomic write to target file
        try:
            write_raw_file_atomically(target_path, raw_bytes)
        except Exception as e:
            print(
                f"Failed writing atomic file {target_path}: {e}",
                file=sys.stderr,
            )
            append_jsonl(
                failures_path,
                {
                    "fetch_time_utc": fetch_time_str,
                    "station_id": station_id,
                    "sensor_id": sensor_id,
                    "parameter": parameter,
                    "url": url,
                    "http_status": status_code,
                    "error": "atomic_write_failed",
                    "error_detail": str(e),
                },
            )
            failures += 1
            break

        results = parsed_data.get("results", [])
        result_count = len(results)

        # Compute digest and log to manifest
        sha256 = hashlib.sha256(raw_bytes).hexdigest()
        manifest_entry = {
            "fetch_time_utc": fetch_time_str,
            "station_id": station_id,
            "sensor_id": sensor_id,
            "parameter": parameter,
            "url": url,
            "http_status": status_code,
            "sha256": sha256,
            "file_path": normalized_file_path,
            "datetime_from": datetime_from,
            "datetime_to": datetime_to,
            "page": page,
            "result_count": result_count,
        }
        append_jsonl(manifest_path, manifest_entry)
        files_saved += 1

        # Check paging condition: request next page ONLY when len(results) == limit
        if result_count < limit or result_count == 0:
            break
        page += 1

    return files_saved, failures


def run_observation_history(
    stations_csv: str = "data/stations_candidates.csv",
    raw_locations_dir: str = "data/raw",
    config_path: str = DEFAULT_HISTORY_CONFIG_PATH,
    raw_dir: str = "data/raw/openaq",
    parameters: list[str] | None = None,
    max_requests: int | None = None,
    limit: int = 1000,
    dry_run: bool = False,
    yes: bool = False,
    now_utc: datetime | None = None,
    min_disk_gb: float = DEFAULT_MIN_DISK_GB,
    manifest_path: str | None = None,
    failures_path: str | None = None,
    report_path: str = "reports/history_plan.md",
) -> int:
    """Run full observation history ingestion across all active stations."""
    if manifest_path is None:
        manifest_path = os.path.join(raw_dir, "manifest.jsonl")
    if failures_path is None:
        failures_path = os.path.join(raw_dir, "failures.jsonl")

    config = load_history_config(config_path)
    from_date = config.get("from_date", "2024-01-01")
    window_days = int(config.get("window_days", 35))
    spacing_sec = float(config.get("request_spacing", 1.1))

    if max_requests is None:
        max_requests = int(config.get("max_requests_per_run", 1200))

    if parameters is None:
        parameters = ["pm25"]

    if now_utc is None:
        now_utc = datetime.now(UTC)

    # 1. Build observation plan and write report
    planned_windows, missing_sensors = build_station_history_plan(
        stations_csv=stations_csv,
        raw_locations_dir=raw_locations_dir,
        parameters=parameters,
        from_date=from_date,
        window_days=window_days,
        now_utc=now_utc,
    )
    write_history_plan_report(
        planned_windows=planned_windows,
        missing_sensors=missing_sensors,
        report_path=report_path,
        config=config,
        parameters=parameters,
    )

    # 2. Check manifest for completed windows
    completed_requests = read_manifest_completed_requests(manifest_path)
    pending_windows = [
        w
        for w in planned_windows
        if (w["sensor_id"], w["datetime_from"], w["datetime_to"], 1)
        not in completed_requests
    ]

    distinct_stations = len({w["station_id"] for w in planned_windows})
    distinct_sensors = len({w["sensor_id"] for w in planned_windows})
    total_planned = len(planned_windows)
    pending_count = len(pending_windows)
    completed_count = total_planned - pending_count
    est_requests = pending_count
    est_minutes = (est_requests * spacing_sec) / 60.0

    # 3. Check disk space
    has_disk_space, free_gb = check_disk_space(raw_dir, min_gb=min_disk_gb)

    # Print plan banner
    print("\n================ OBSERVATION HISTORY PLAN ================")
    print(f"Stations: {distinct_stations} (active monitors with decision=='use')")
    print(f"Sensors: {distinct_sensors} (parameters: {', '.join(parameters)})")
    print(f"Total Windows: {total_planned}")
    print(f"Completed Windows: {completed_count}")
    print(f"Pending Windows: {pending_count}")
    print(f"Estimated Requests: {est_requests}")
    print(f"Estimated Duration: ~{est_minutes:.1f} minutes (at {spacing_sec}s spacing)")
    print(f"Free Disk Space: {free_gb:.2f} GB (minimum required: {min_disk_gb:.1f} GB)")
    print("==========================================================")

    # 4. Enforce disk guard
    if not has_disk_space:
        print(
            f"Error: Free disk space ({free_gb:.2f} GB) is below the "
            f"{min_disk_gb:.1f} GB minimum threshold. Ingestion refused.",
            file=sys.stderr,
        )
        return 1

    # 5. Guard: If requests > 200, require --yes
    if est_requests > 200 and not dry_run and not yes:
        print(
            f"Error: Plan requires ~{est_requests} requests (> 200). "
            f"Pass --yes to proceed with live execution.",
            file=sys.stderr,
        )
        params_flag = ",".join(parameters)
        print(
            f"REMAINING windows: {pending_count}\n"
            f"To resume, run:\n"
            f"  python -m ingest.fetch_observations --parameters {params_flag} --yes"
        )
        return 1

    params_flag = ",".join(parameters)
    resume_cmd = f"python -m ingest.fetch_observations --parameters {params_flag} --yes"

    # 6. Dry-run handling
    if dry_run:
        print("\n[DRY-RUN] Planned URLs for pending windows:")
        for w in pending_windows[:20]:
            sample_url = build_hours_url(
                sensor_id=w["sensor_id"],
                datetime_from=w["datetime_from"],
                datetime_to=w["datetime_to"],
                limit=limit,
                page=1,
            )
            print(
                f"[DRY-RUN] station={w['station_id']} sensor={w['sensor_id']} "
                f"param={w['parameter']} from={w['datetime_from']} "
                f"to={w['datetime_to']}"
            )
            print(f"[DRY-RUN] URL: {sample_url}")
        if len(pending_windows) > 20:
            print(f"[DRY-RUN] ... and {len(pending_windows) - 20} more windows.")
        print(f"\nREMAINING windows: {pending_count}")
        print(f"To resume, run:\n  {resume_cmd}")
        return 0

    # 7. Live execution
    api_key = get_api_key()
    tracker = RequestTracker(max_requests=max_requests)

    total_saved = 0
    total_failures = 0

    for w in pending_windows:
        if tracker.count >= tracker.max_requests:
            print(
                "Notice: Configured request cap reached for this run.",
                file=sys.stderr,
            )
            break
        try:
            saved, failed = fetch_sensor_hours(
                station_id=w["station_id"],
                sensor_id=w["sensor_id"],
                parameter=w["parameter"],
                datetime_from=w["datetime_from"],
                datetime_to=w["datetime_to"],
                api_key=api_key,
                raw_dir=raw_dir,
                tracker=tracker,
                fetch_dt=now_utc,
                limit=limit,
                dry_run=False,
                manifest_path=manifest_path,
                failures_path=failures_path,
                completed_requests=completed_requests,
            )
            total_saved += saved
            total_failures += failed
            if tracker.last_status_code == 401:
                print(
                    "Error: API key rejected. Halting observation history ingestion.",
                    file=sys.stderr,
                )
                break
            if tracker.count >= tracker.max_requests:
                print(
                    "Notice: Configured request cap reached for this run.",
                    file=sys.stderr,
                )
                break
        except RequestCapExceededError:
            print(
                "Notice: Configured request cap reached for this run.",
                file=sys.stderr,
            )
            break

    # Re-evaluate remaining windows after execution
    completed_after = read_manifest_completed_requests(manifest_path)
    remaining_count = sum(
        1
        for w in planned_windows
        if (w["sensor_id"], w["datetime_from"], w["datetime_to"], 1)
        not in completed_after
    )

    print("\n================ RUN SUMMARY ================")
    print(f"Files saved: {total_saved}")
    print(f"Failures recorded: {total_failures}")
    print(f"HTTP requests made: {tracker.count}/{tracker.max_requests}")
    print(f"REMAINING windows: {remaining_count}")
    print(f"To resume, run:\n  {resume_cmd}")

    if total_failures > 0:
        return 1
    return 0


def run_observation_pilot(
    datetime_from: str,
    datetime_to: str,
    raw_dir: str = "data/raw/openaq",
    stations: list[dict[str, Any]] | None = None,
    max_requests: int = DEFAULT_MAX_REQUESTS,
    limit: int = 1000,
    dry_run: bool = False,
    now_utc: datetime | None = None,
) -> int:
    """Run observation pilot across stations.

    Returns exit code (0 on success, 1 on failure).
    """
    if stations is None:
        stations = DEFAULT_PILOT_STATIONS

    if now_utc is None:
        now_utc = datetime.now(UTC)

    dt_from_norm = normalize_iso_utc(datetime_from, is_end_of_day=False)
    dt_to_norm = normalize_iso_utc(datetime_to, is_end_of_day=True)

    api_key = ""
    if not dry_run:
        api_key = get_api_key()

    tracker = RequestTracker(max_requests=max_requests)

    total_saved = 0
    total_failures = 0
    skipped_pm10: list[int] = []

    print(
        f"Starting observation pilot fetch: from={dt_from_norm} "
        f"to={dt_to_norm} (dry_run={dry_run})"
    )

    for st in stations:
        sid = st["station_id"]
        sname = st.get("name", "Unknown")
        sensors = st.get("sensors", {})

        print(f"\n--- Station {sid} ({sname}) ---")

        # 1. PM2.5
        pm25_sensor = sensors.get("pm25")
        if pm25_sensor is not None:
            saved, failed = fetch_sensor_hours(
                station_id=sid,
                sensor_id=pm25_sensor,
                parameter="pm25",
                datetime_from=dt_from_norm,
                datetime_to=dt_to_norm,
                api_key=api_key,
                raw_dir=raw_dir,
                tracker=tracker,
                fetch_dt=now_utc,
                limit=limit,
                dry_run=dry_run,
            )
            total_saved += saved
            total_failures += failed
        else:
            print(f"Station {sid}: no PM2.5 sensor (skipped)")

        # 2. PM10
        pm10_sensor = sensors.get("pm10")
        if pm10_sensor is not None:
            saved, failed = fetch_sensor_hours(
                station_id=sid,
                sensor_id=pm10_sensor,
                parameter="pm10",
                datetime_from=dt_from_norm,
                datetime_to=dt_to_norm,
                api_key=api_key,
                raw_dir=raw_dir,
                tracker=tracker,
                fetch_dt=now_utc,
                limit=limit,
                dry_run=dry_run,
            )
            total_saved += saved
            total_failures += failed
        else:
            print(f"Station {sid}: no PM10 sensor (skipped)")
            skipped_pm10.append(sid)

    # Print run summary
    print("\n================ RUN SUMMARY ================")
    print(f"Files saved: {total_saved}")
    print(f"Failures recorded: {total_failures}")
    print(f"HTTP requests made: {tracker.count}/{tracker.max_requests}")
    if skipped_pm10:
        print(f"Stations with no PM10 sensor (skipped): {skipped_pm10}")
    if tracker.count >= tracker.max_requests:
        print(
            "Warning: Request cap (--max-requests) was reached during the run.",
            file=sys.stderr,
        )

    if total_failures > 0 or tracker.count >= tracker.max_requests:
        return 1
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Fetch historical PM2.5 and PM10 observations from OpenAQ API v3."
    )
    parser.add_argument(
        "--from",
        dest="from_date",
        default=None,
        help="Start UTC date or datetime (e.g. 2026-11-01 or 2026-11-01T00:00:00Z)",
    )
    parser.add_argument(
        "--to",
        dest="to_date",
        default=None,
        help="End UTC date or datetime (e.g. 2026-11-07 or 2026-11-07T23:59:59Z)",
    )
    parser.add_argument(
        "--parameters",
        default="pm25",
        help="Comma-separated target parameters (default: pm25; e.g. pm25,pm10)",
    )
    parser.add_argument(
        "--config",
        default=DEFAULT_HISTORY_CONFIG_PATH,
        help=f"Path to history config JSON (default: {DEFAULT_HISTORY_CONFIG_PATH})",
    )
    parser.add_argument(
        "--stations-csv",
        default="data/stations_candidates.csv",
        help="Path to stations candidates CSV (default: data/stations_candidates.csv)",
    )
    parser.add_argument(
        "--raw-locations-dir",
        default="data/raw",
        help="Directory holding raw location discovery JSON files (default: data/raw)",
    )
    parser.add_argument(
        "--raw-dir",
        default="data/raw/openaq",
        help="Raw observation output directory (default: data/raw/openaq)",
    )
    parser.add_argument(
        "--max-requests",
        type=int,
        default=None,
        help="Max allowed HTTP requests across run",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="Results limit per API page (default: 1000)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print query URLs and target paths without making network calls",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm execution when plan exceeds 200 requests",
    )
    parser.add_argument(
        "--pilot",
        action="store_true",
        help="Force pilot mode execution across the 5 default pilot stations",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Entry point for CLI execution."""
    args = parse_args(argv)

    # Determine whether to execute pilot mode or full observation history
    # If explicit --pilot, or both --from and --to provided without --parameters:
    is_explicit_pilot = args.pilot or (
        args.from_date is not None
        and args.to_date is not None
        and args.parameters == "pm25"
        and not args.yes
    )

    if is_explicit_pilot:
        from_str = args.from_date or "2026-11-01"
        to_str = args.to_date or "2026-11-07"
        max_req = args.max_requests or DEFAULT_MAX_REQUESTS
        return run_observation_pilot(
            datetime_from=from_str,
            datetime_to=to_str,
            raw_dir=args.raw_dir,
            max_requests=max_req,
            limit=args.limit,
            dry_run=args.dry_run,
        )

    # Otherwise run full observation history mode
    params_list = [p.strip().lower() for p in args.parameters.split(",") if p.strip()]
    return run_observation_history(
        stations_csv=args.stations_csv,
        raw_locations_dir=args.raw_locations_dir,
        config_path=args.config,
        raw_dir=args.raw_dir,
        parameters=params_list,
        max_requests=args.max_requests,
        limit=args.limit,
        dry_run=args.dry_run,
        yes=args.yes,
    )


if __name__ == "__main__":
    sys.exit(main())
