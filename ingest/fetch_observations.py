"""Fetch historical hourly PM2.5 and PM10 observations from OpenAQ API v3.

WP3 pilot implementation: fetches observations for Delhi-NCR pilot stations,
saving raw responses atomically to:
  data/raw/openaq/<station_id>/<sensor_id>/<fetch_time_utc>_p<page>.json
and logging immutable audit records to data/raw/openaq/manifest.jsonl.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from typing import Any

API_BASE = "https://api.openaq.org/v3"
USER_AGENT = "NCR-Hawa-ObservationPilot/0.1"
DEFAULT_DELAY_SEC = 1.1
DEFAULT_TIMEOUT_SEC = 15.0
DEFAULT_MAX_REQUESTS = 60

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


class RequestTracker:
    """Tracks number of HTTP requests and enforces max request cap and timing."""

    def __init__(self, max_requests: int = DEFAULT_MAX_REQUESTS) -> None:
        self.max_requests = max_requests
        self.count = 0
        self.last_request_time: float | None = None

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
                return resp.status, raw_bytes, resp_headers
        except urllib.error.HTTPError as e:
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
) -> tuple[int, int]:
    """Fetch all pages for a single sensor and save atomically to archive.

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

        # Check existence before making the request (never overwrite)
        if os.path.exists(target_path):
            print(f"Skipping existing file (idempotent): {normalized_file_path}")
            # Stop page chain since target already exists
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
        }
        append_jsonl(manifest_path, manifest_entry)
        files_saved += 1

        # Check if another page is needed
        results = parsed_data.get("results", [])
        if len(results) < limit or len(results) == 0:
            break
        page += 1

    return files_saved, failures


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
        required=True,
        help="Start UTC date or datetime (e.g. 2026-11-01 or 2026-11-01T00:00:00Z)",
    )
    parser.add_argument(
        "--to",
        dest="to_date",
        required=True,
        help="End UTC date or datetime (e.g. 2026-11-07 or 2026-11-07T23:59:59Z)",
    )
    parser.add_argument(
        "--raw-dir",
        default="data/raw/openaq",
        help="Raw observation output directory (default: data/raw/openaq)",
    )
    parser.add_argument(
        "--max-requests",
        type=int,
        default=DEFAULT_MAX_REQUESTS,
        help=f"Max allowed HTTP requests across run (default: {DEFAULT_MAX_REQUESTS})",
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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Entry point for CLI execution."""
    args = parse_args(argv)
    return run_observation_pilot(
        datetime_from=args.from_date,
        datetime_to=args.to_date,
        raw_dir=args.raw_dir,
        max_requests=args.max_requests,
        limit=args.limit,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    sys.exit(main())
