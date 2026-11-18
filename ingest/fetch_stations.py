"""Fetch monitoring locations in Delhi-NCR from OpenAQ API v3 and record licences."""

from __future__ import annotations

import argparse
import csv
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
USER_AGENT = "NCR-Hawa-StationAudit/0.1"

# Geospatial bounding box for Delhi-NCR in WGS 84 coordinates: minX, minY, maxX, maxY
# (Unverified snippet notes; confirm in live deployment tests)
DEFAULT_DELHI_NCR_BBOX = "76.5,27.8,78.2,29.2"

# Free-tier rate limits (e.g. 60/min, 2,000/hour) are UNVERIFIED search estimates.
# Do not hard-code them; enforce runtime delay and backoff on 429 response.
DEFAULT_REQUEST_DELAY_SEC = 1.1

CSV_COLUMNS = [
    "station_id",
    "name",
    "provider",
    "lat",
    "lon",
    "licence_name",
    "commercialUseAllowed",
    "attributionRequired",
    "redistributionAllowed",
    "source_url",
    "checked_on",
    "decision",
    "is_monitor",
    "is_mobile",
    "has_pm25",
    "datetime_first",
    "datetime_last",
]


def get_api_key() -> str:
    """Read API key from environment without printing or leaking secrets."""
    key = os.environ.get("OPENAQ_API_KEY", "").strip()
    if not key:
        print("Error: OPENAQ_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)
    return key


def parse_found(val: Any) -> tuple[int | None, str]:
    """Parse meta.found defensively.

    Accepts int, numeric string, '>100' (meaning more than 100, total unknown),
    None or anything else (treated as unknown). Never raises ValueError.
    """
    if val is None:
        return None, "unknown"
    if isinstance(val, int):
        return val, str(val)
    if isinstance(val, str):
        val_clean = val.strip()
        if val_clean.startswith(">"):
            return None, val_clean
        try:
            parsed = int(val_clean)
            return parsed, str(parsed)
        except ValueError:
            return None, "unknown"
    return None, "unknown"


def save_raw_response(filepath: str, data: dict[str, Any]) -> None:
    """Write raw response JSON payload to disk without headers or secrets."""
    parent = os.path.dirname(filepath)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def make_request(
    url: str,
    api_key: str,
    timeout: float = 15.0,
    max_retries: int = 3,
    delay_sec: float = DEFAULT_REQUEST_DELAY_SEC,
) -> dict[str, Any]:
    """Execute GET request with rate limiting delay, backoff, and auth header."""
    headers = {
        "User-Agent": USER_AGENT,
        "X-API-Key": api_key,
        "Accept": "application/json",
    }
    req = urllib.request.Request(url, headers=headers)

    for attempt in range(max_retries + 1):
        try:
            if delay_sec > 0:
                time.sleep(delay_sec)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw_bytes = resp.read()
                return json.loads(raw_bytes.decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 401:
                # Strictly avoid leaking key, headers, or URL query secrets
                print("API key rejected", file=sys.stderr)
                sys.exit(1)
            if e.code == 429:
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
                    time.sleep(wait_sec)
                    continue
                print(
                    "Error: Rate limit exceeded (429) and max retries reached.",
                    file=sys.stderr,
                )
                sys.exit(1)
            print(f"HTTP error {e.code}", file=sys.stderr)
            sys.exit(1)
        except urllib.error.URLError as e:
            if attempt < max_retries:
                time.sleep(2.0 ** (attempt + 1))
                continue
            print(f"Network error: {e.reason}", file=sys.stderr)
            sys.exit(1)

    print("Error: Max retries exceeded.", file=sys.stderr)
    sys.exit(1)


def fetch_all_licenses(
    api_key: str,
    timeout: float = 15.0,
    delay_sec: float = DEFAULT_REQUEST_DELAY_SEC,
    save_raw: bool = False,
    raw_dir: str = "data/raw",
) -> dict[int, dict[str, Any]]:
    """Fetch global licenses from /v3/licenses and index by integer ID."""
    url = f"{API_BASE}/licenses?limit=100"
    data = make_request(url, api_key=api_key, timeout=timeout, delay_sec=delay_sec)

    if save_raw:
        ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        filename = f"licenses_{ts}.json"
        save_raw_response(os.path.join(raw_dir, filename), data)

    licenses_map: dict[int, dict[str, Any]] = {}
    for item in data.get("results", []):
        lic_id = item.get("id")
        if lic_id is not None:
            licenses_map[int(lic_id)] = item
    return licenses_map


def fetch_license_by_id(
    lic_id: int,
    api_key: str,
    timeout: float = 15.0,
    delay_sec: float = DEFAULT_REQUEST_DELAY_SEC,
    save_raw: bool = False,
    raw_dir: str = "data/raw",
) -> dict[str, Any]:
    """Fetch a single license record by ID."""
    url = f"{API_BASE}/licenses/{lic_id}"
    data = make_request(url, api_key=api_key, timeout=timeout, delay_sec=delay_sec)

    if save_raw:
        ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        filename = f"license_{lic_id}_{ts}.json"
        save_raw_response(os.path.join(raw_dir, filename), data)

    results = data.get("results", [])
    if results and isinstance(results, list):
        return results[0]
    return {}


def fetch_locations(
    bbox: str,
    api_key: str,
    max_pages: int = 5,
    timeout: float = 15.0,
    delay_sec: float = DEFAULT_REQUEST_DELAY_SEC,
    save_raw: bool = False,
    raw_dir: str = "data/raw",
) -> tuple[list[dict[str, Any]], str]:
    """Fetch locations matching bbox using pagination.

    Stops when a page returns 0 results or fewer results than limit (100),
    or when max_pages is hit. Does not rely on meta.found to terminate.
    """
    locations: list[dict[str, Any]] = []
    limit = 100
    found_display = "unknown"

    for page in range(1, max_pages + 1):
        params = urllib.parse.urlencode(
            {
                "bbox": bbox,
                "limit": limit,
                "page": page,
            }
        )
        url = f"{API_BASE}/locations?{params}"
        data = make_request(url, api_key=api_key, timeout=timeout, delay_sec=delay_sec)

        if save_raw:
            ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            filename = f"locations_{ts}_page_{page}.json"
            save_raw_response(os.path.join(raw_dir, filename), data)

        meta = data.get("meta", {})
        if page == 1 and "found" in meta:
            _, found_display = parse_found(meta.get("found"))

        results = data.get("results", [])
        if not isinstance(results, list) or len(results) == 0:
            break

        locations.extend(results)

        # Stop if page has fewer results than requested limit
        if len(results) < limit:
            break

        # If we reached max_pages and a full page was returned
        if page == max_pages and len(results) == limit:
            print(
                f"Warning: Reached --max-pages ({max_pages}) with a full page "
                "returned. The station list may be incomplete.",
                file=sys.stderr,
            )

    return locations, found_display


def format_flag(val: Any) -> str:
    """Format boolean flag; if absent or None, write empty string, never False."""
    if val is None or val == "":
        return ""
    if isinstance(val, bool):
        return str(val)
    return str(val)


def build_csv_rows(
    locations: list[dict[str, Any]],
    licenses_map: dict[int, dict[str, Any]],
    api_key: str,
    checked_on: str,
    timeout: float = 15.0,
    delay_sec: float = DEFAULT_REQUEST_DELAY_SEC,
    save_raw: bool = False,
    raw_dir: str = "data/raw",
) -> list[dict[str, str]]:
    """Transform locations and joined licences into CSV rows."""
    rows: list[dict[str, str]] = []

    for loc in locations:
        station_id = str(loc.get("id", ""))
        name = str(loc.get("name", ""))

        provider_obj = loc.get("provider")
        provider_name = (
            str(provider_obj.get("name", ""))
            if isinstance(provider_obj, dict)
            else str(provider_obj or "")
        )

        coords = loc.get("coordinates") or {}
        lat = str(coords.get("latitude", ""))
        lon = str(coords.get("longitude", ""))

        is_monitor = loc.get("isMonitor")
        is_monitor_str = "" if is_monitor is None else str(is_monitor)

        is_mobile = loc.get("isMobile")
        is_mobile_str = "" if is_mobile is None else str(is_mobile)

        sensors = loc.get("sensors") or []
        has_pm25 = any(
            isinstance(s, dict)
            and "pm25"
            in str(s.get("parameter", {}).get("name", "")).lower().replace(".", "")
            for s in sensors
        )
        has_pm25_str = str(has_pm25) if sensors else ""

        dt_first = loc.get("datetimeFirst")
        dt_first_str = (
            dt_first.get("utc", "")
            if isinstance(dt_first, dict)
            else str(dt_first or "")
        )

        dt_last = loc.get("datetimeLast")
        dt_last_str = (
            dt_last.get("utc", "") if isinstance(dt_last, dict) else str(dt_last or "")
        )

        loc_licenses = loc.get("licenses") or []
        if not loc_licenses:
            rows.append(
                {
                    "station_id": station_id,
                    "name": name,
                    "provider": provider_name,
                    "lat": lat,
                    "lon": lon,
                    "licence_name": "",
                    "commercialUseAllowed": "",
                    "attributionRequired": "",
                    "redistributionAllowed": "",
                    "source_url": "",
                    "checked_on": checked_on,
                    "decision": "",
                    "is_monitor": is_monitor_str,
                    "is_mobile": is_mobile_str,
                    "has_pm25": has_pm25_str,
                    "datetime_first": dt_first_str,
                    "datetime_last": dt_last_str,
                }
            )
        else:
            for loc_lic in loc_licenses:
                lic_id = loc_lic.get("id")
                lic_details = {}
                if lic_id is not None:
                    lic_id_int = int(lic_id)
                    if lic_id_int in licenses_map:
                        lic_details = licenses_map[lic_id_int]
                    else:
                        lic_details = fetch_license_by_id(
                            lic_id_int,
                            api_key=api_key,
                            timeout=timeout,
                            delay_sec=delay_sec,
                            save_raw=save_raw,
                            raw_dir=raw_dir,
                        )
                        licenses_map[lic_id_int] = lic_details

                lic_name = str(lic_details.get("name") or loc_lic.get("name", "") or "")
                comm = format_flag(lic_details.get("commercialUseAllowed"))
                attr = format_flag(lic_details.get("attributionRequired"))
                redist = format_flag(lic_details.get("redistributionAllowed"))
                src_url = str(lic_details.get("sourceUrl") or "")

                rows.append(
                    {
                        "station_id": station_id,
                        "name": name,
                        "provider": provider_name,
                        "lat": lat,
                        "lon": lon,
                        "licence_name": lic_name,
                        "commercialUseAllowed": comm,
                        "attributionRequired": attr,
                        "redistributionAllowed": redist,
                        "source_url": src_url,
                        "checked_on": checked_on,
                        "decision": "",
                        "is_monitor": is_monitor_str,
                        "is_mobile": is_mobile_str,
                        "has_pm25": has_pm25_str,
                        "datetime_first": dt_first_str,
                        "datetime_last": dt_last_str,
                    }
                )

    return rows


def write_csv(output_path: str, rows: list[dict[str, str]]) -> None:
    """Write rows to output CSV file preserving exact column schema."""
    parent = os.path.dirname(output_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def print_summary(rows: list[dict[str, str]]) -> None:
    """Print summary of fetched stations, licences, and flag distributions."""
    station_ids = {r["station_id"] for r in rows if r["station_id"]}
    print("\n--- Station & Licence Audit Summary ---")
    print(f"Total stations fetched: {len(station_ids)}")
    print(f"Total rows written: {len(rows)}")

    licence_counts: dict[str, int] = {}
    comm_counts: dict[str, int] = {}
    attr_counts: dict[str, int] = {}
    redist_counts: dict[str, int] = {}

    for r in rows:
        lic = r["licence_name"] or "(no licence listed)"
        licence_counts[lic] = licence_counts.get(lic, 0) + 1

        c = r["commercialUseAllowed"] or "(unset/empty)"
        comm_counts[c] = comm_counts.get(c, 0) + 1

        a = r["attributionRequired"] or "(unset/empty)"
        attr_counts[a] = attr_counts.get(a, 0) + 1

        rd = r["redistributionAllowed"] or "(unset/empty)"
        redist_counts[rd] = redist_counts.get(rd, 0) + 1

    print("\nDistinct Licences (with row count):")
    for lic, count in sorted(licence_counts.items(), key=lambda x: -x[1]):
        print(f"  - {lic}: {count}")

    print("\nFlag Counts (per row):")
    print("  commercialUseAllowed:")
    for k, v in sorted(comm_counts.items()):
        print(f"    {k}: {v}")
    print("  attributionRequired:")
    for k, v in sorted(attr_counts.items()):
        print(f"    {k}: {v}")
    print("  redistributionAllowed:")
    for k, v in sorted(redist_counts.items()):
        print(f"    {k}: {v}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch monitoring locations in Delhi-NCR from OpenAQ API v3."
    )
    parser.add_argument(
        "--output",
        default="data/licences.csv",
        help="Path to output CSV file (default: data/licences.csv).",
    )
    parser.add_argument(
        "--bbox",
        default=DEFAULT_DELHI_NCR_BBOX,
        help="Bounding box in minX,minY,maxX,maxY format.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=5,
        help="Maximum pages to fetch as a request cap (default: 5).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="Request timeout in seconds (default: 15.0).",
    )
    parser.add_argument(
        "--save-raw",
        action="store_true",
        help="Save raw JSON responses to data/raw/ (without headers or keys).",
    )
    parser.add_argument(
        "--raw-dir",
        default="data/raw",
        help="Directory to save raw JSON responses (default: data/raw).",
    )
    return parser.parse_args(argv)


def run_audit(
    output_path: str,
    bbox: str,
    max_pages: int = 5,
    timeout: float = 15.0,
    delay_sec: float = DEFAULT_REQUEST_DELAY_SEC,
    save_raw: bool = False,
    raw_dir: str = "data/raw",
) -> list[dict[str, str]]:
    api_key = get_api_key()
    today_utc = datetime.now(UTC).strftime("%Y-%m-%d")

    # 1. Fetch locations
    locations, _ = fetch_locations(
        bbox=bbox,
        api_key=api_key,
        max_pages=max_pages,
        timeout=timeout,
        delay_sec=delay_sec,
        save_raw=save_raw,
        raw_dir=raw_dir,
    )

    # 2. Collect licenses
    licenses_map = fetch_all_licenses(
        api_key=api_key,
        timeout=timeout,
        delay_sec=delay_sec,
        save_raw=save_raw,
        raw_dir=raw_dir,
    )

    # 3. Build joined rows
    rows = build_csv_rows(
        locations=locations,
        licenses_map=licenses_map,
        api_key=api_key,
        checked_on=today_utc,
        timeout=timeout,
        delay_sec=delay_sec,
        save_raw=save_raw,
        raw_dir=raw_dir,
    )

    # 4. Write CSV
    write_csv(output_path, rows)

    # 5. Print summary
    print_summary(rows)

    return rows


def main() -> None:
    args = parse_args()
    run_audit(
        output_path=args.output,
        bbox=args.bbox,
        max_pages=args.max_pages,
        timeout=args.timeout,
        save_raw=args.save_raw,
        raw_dir=args.raw_dir,
    )


if __name__ == "__main__":
    main()
