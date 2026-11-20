"""Archive Open-Meteo CAMS and weather forecasts for Delhi-NCR areas.

NOTE ON ISSUE TIME:
The Open-Meteo API response does not provide the exact numerical model run or cycle
initialization time. For data lineage and leakage prevention, this pipeline treats
the fetch time (in UTC) as the "issue time". We do not claim or infer the model
run time.
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

USER_AGENT = "NCR-Hawa-Archive/0.1"
DEFAULT_DELAY_SEC = 1.0
DEFAULT_TIMEOUT_SEC = 15.0


def load_json_config(path: str) -> dict[str, Any]:
    """Load configuration from JSON file."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_request_url(
    endpoint: str,
    lat: float,
    lon: float,
    hourly_vars: list[str],
    forecast_days: int = 5,
    timezone: str = "UTC",
    domains: str | None = None,
    models: str | list[str] | None = None,
) -> str:
    """Build query URL for Open-Meteo endpoint."""
    params: dict[str, str | int] = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join(hourly_vars),
        "forecast_days": forecast_days,
        "timezone": timezone,
    }
    if domains:
        params["domains"] = domains
    if models:
        if isinstance(models, list):
            params["models"] = ",".join(models)
        else:
            params["models"] = models

    query_str = urllib.parse.urlencode(params)
    return f"{endpoint}?{query_str}"


def validate_response_payload(
    raw_bytes: bytes,
    expected_vars: list[str],
) -> tuple[dict[str, Any] | None, str | None]:
    """Validate that response is valid JSON and contains required hourly fields.

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

    hourly = data.get("hourly")
    if not isinstance(hourly, dict):
        return None, "missing_hourly_section"

    time_col = hourly.get("time")
    if not isinstance(time_col, list) or len(time_col) == 0:
        return None, "missing_or_empty_hourly_time"

    missing_vars = [v for v in expected_vars if v not in hourly]
    if missing_vars:
        return None, f"missing_hourly_variables: {', '.join(missing_vars)}"

    return data, None


def append_jsonl(filepath: str, entry: dict[str, Any]) -> None:
    """Append a JSON line to manifest or failure log."""
    parent = os.path.dirname(filepath)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")


def write_raw_file_atomically(target_path: str, raw_bytes: bytes) -> None:
    """Write raw response bytes to target path atomically via temporary file."""
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


def fetch_with_retries(
    url: str,
    timeout: float = DEFAULT_TIMEOUT_SEC,
    max_retries: int = 3,
    delay_sec: float = DEFAULT_DELAY_SEC,
) -> tuple[int, bytes, str | None]:
    """Fetch URL with retries on 429 and 5xx.

    Returns (status_code, response_bytes, error_reason).
    """
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    for attempt in range(max_retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = resp.status if hasattr(resp, "status") else 200
                raw = resp.read()
                return status, raw, None
        except urllib.error.HTTPError as e:
            # 400 Client Error -> do not retry
            if e.code == 400:
                error_body = ""
                try:
                    error_body = e.read().decode("utf-8")
                except Exception:
                    pass
                return 400, b"", f"HTTP 400 Bad Request: {error_body or e.reason}"

            # 429 or 5xx -> retry with exponential backoff
            if e.code == 429 or 500 <= e.code < 600:
                if attempt < max_retries:
                    retry_after = e.headers.get("Retry-After") if e.headers else None
                    try:
                        wait_sec = (
                            float(retry_after)
                            if retry_after
                            else (2.0 ** (attempt + 1))
                        )
                    except ValueError:
                        wait_sec = 2.0 ** (attempt + 1)
                    if delay_sec == 0.0:
                        wait_sec = 0.0
                    if wait_sec > 0:
                        time.sleep(wait_sec)
                    continue
                return e.code, b"", f"HTTP {e.code} after {max_retries} retries"

            # Other HTTP error
            return e.code, b"", f"HTTP {e.code}: {e.reason}"

        except urllib.error.URLError as e:
            if attempt < max_retries:
                if delay_sec > 0:
                    time.sleep(2.0 ** (attempt + 1))
                continue
            return 0, b"", f"Network error: {e.reason}"

    return 0, b"", "Max retries exceeded"


def archive_forecasts(
    areas_path: str = "configs/areas.json",
    vars_path: str = "configs/variables.json",
    raw_dir: str = "data/raw/open_meteo",
    timeout: float = DEFAULT_TIMEOUT_SEC,
    delay_sec: float = DEFAULT_DELAY_SEC,
    dry_run: bool = False,
    now_utc: datetime | None = None,
) -> dict[str, int]:
    """Execute forecast archive run across areas and sources."""
    areas_data = load_json_config(areas_path)
    vars_data = load_json_config(vars_path)
    areas = areas_data.get("areas", [])

    current_time = now_utc or datetime.now(UTC)
    fetch_time_iso = current_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    fetch_time_file = current_time.strftime("%Y%m%d%H%M00Z")

    manifest_path = os.path.join(raw_dir, "manifest.jsonl")
    failures_path = os.path.join(raw_dir, "failures.jsonl")

    stats = {"success": 0, "skipped": 0, "failed": 0}

    sources_to_run = ["cams", "weather"]

    for area in areas:
        area_id = area["area_id"]
        lat = area["latitude"]
        lon = area["longitude"]

        for source in sources_to_run:
            if source not in vars_data:
                continue
            src_config = vars_data[source]
            endpoint = src_config["endpoint"]
            hourly_vars = src_config["hourly"]
            forecast_days = src_config.get("forecast_days", 5)
            timezone = src_config.get("timezone", "UTC")
            domains = src_config.get("domains")
            models_config = src_config.get("models")

            # Determine task list of (model_name, folder_name)
            # If models_config is defined, iterate over configured models.
            # If models_config is absent/None, run once with "default" model.
            tasks: list[tuple[str, str]] = []
            if models_config:
                if isinstance(models_config, list):
                    for m_item in models_config:
                        if isinstance(m_item, dict):
                            tasks.append(
                                (
                                    m_item["model"],
                                    m_item.get("folder", f"{source}_{m_item['model']}"),
                                )
                            )
                        elif isinstance(m_item, str):
                            tasks.append((m_item, f"{source}_{m_item}"))
                elif isinstance(models_config, dict):
                    for folder_name, m_name in models_config.items():
                        tasks.append((m_name, folder_name))
            else:
                tasks.append(("default", source))

            for model_name, target_folder in tasks:
                models_param = None if model_name == "default" else model_name
                url = build_request_url(
                    endpoint=endpoint,
                    lat=lat,
                    lon=lon,
                    hourly_vars=hourly_vars,
                    forecast_days=forecast_days,
                    timezone=timezone,
                    domains=domains,
                    models=models_param,
                )

                target_path = os.path.join(
                    raw_dir, target_folder, area_id, f"{fetch_time_file}.json"
                )

                if dry_run:
                    print(
                        f"[DRY RUN] source={source} area={area_id} "
                        f"model={model_name} target={target_path} url={url}"
                    )
                    continue

                # Check if target file already exists BEFORE making request
                if os.path.exists(target_path):
                    print(
                        f"Skipping {source}/{model_name}/{area_id}: "
                        f"{target_path} already exists for this minute."
                    )
                    stats["skipped"] += 1
                    continue

                # Respect request rate limit delay
                if delay_sec > 0:
                    time.sleep(delay_sec)

                # Perform network fetch
                status_code, raw_bytes, error_reason = fetch_with_retries(
                    url, timeout=timeout, delay_sec=delay_sec
                )

                if status_code != 200:
                    print(
                        f"Failure fetching {source}/{model_name}/{area_id} "
                        f"(HTTP {status_code}): {error_reason}",
                        file=sys.stderr,
                    )
                    append_jsonl(
                        failures_path,
                        {
                            "fetch_time_utc": fetch_time_iso,
                            "source": source,
                            "area_id": area_id,
                            "model": model_name,
                            "url": url,
                            "http_status": status_code,
                            "reason": error_reason or "http_failure",
                        },
                    )
                    stats["failed"] += 1
                    continue

                # Validate response payload
                _, val_err = validate_response_payload(raw_bytes, hourly_vars)
                if val_err:
                    print(
                        f"Validation failed for {source}/{model_name}/{area_id}: "
                        f"{val_err}",
                        file=sys.stderr,
                    )
                    append_jsonl(
                        failures_path,
                        {
                            "fetch_time_utc": fetch_time_iso,
                            "source": source,
                            "area_id": area_id,
                            "model": model_name,
                            "url": url,
                            "http_status": 200,
                            "reason": val_err,
                        },
                    )
                    stats["failed"] += 1
                    continue

                # Write file atomically
                write_raw_file_atomically(target_path, raw_bytes)

                # Record in manifest
                sha256_hash = hashlib.sha256(raw_bytes).hexdigest()
                append_jsonl(
                    manifest_path,
                    {
                        "fetch_time_utc": fetch_time_iso,
                        "source": source,
                        "area_id": area_id,
                        "model": model_name,
                        "request_url_has_models": "models=" in url,
                        "url": url,
                        "http_status": 200,
                        "sha256": sha256_hash,
                        "file_path": target_path.replace("\\", "/"),
                    },
                )
                stats["success"] += 1

    return stats


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Archive Open-Meteo CAMS and weather forecasts."
    )
    parser.add_argument(
        "--areas",
        default="configs/areas.json",
        help="Path to areas JSON configuration.",
    )
    parser.add_argument(
        "--vars",
        default="configs/variables.json",
        help="Path to variables JSON configuration.",
    )
    parser.add_argument(
        "--raw-dir",
        default="data/raw/open_meteo",
        help="Root storage directory for raw Open-Meteo data.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SEC,
        help="Network request timeout in seconds (default: 15.0).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_DELAY_SEC,
        help="Delay in seconds between requests (default: 1.0).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned URLs and target paths without making network calls.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    stats = archive_forecasts(
        areas_path=args.areas,
        vars_path=args.vars,
        raw_dir=args.raw_dir,
        timeout=args.timeout,
        delay_sec=args.delay,
        dry_run=args.dry_run,
    )
    if not args.dry_run:
        print(
            f"Archive run finished: {stats['success']} saved, "
            f"{stats['skipped']} skipped, {stats['failed']} failed."
        )
    if stats["failed"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
