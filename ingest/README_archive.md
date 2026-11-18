# Open-Meteo Forecast Archive

This directory contains ingestion tooling to periodically archive CAMS global air quality forecasts and numerical weather prediction forecasts for Delhi-NCR monitoring points.

## Important Note on "Issue Time"

The Open-Meteo API response does not report the exact meteorological model run/cycle time (e.g., 00Z or 12Z CAMS initialization). 

Therefore, in our data pipeline:
- We record and treat the **fetch timestamp in UTC** as the **"issue time"** for the archived issuance.
- We do **not** claim or infer the meteorological model run time.
- All downstream features must strictly rely on this fetch timestamp to prevent data leakage (features only use issuances fetched prior to forecast target days).

## Raw Storage Layout

Raw payloads are stored under `data/raw/open_meteo/`:
- `data/raw/open_meteo/cams/<area_id>/<YYYYMMDDTHHMM00Z>.json`
- `data/raw/open_meteo/weather/<area_id>/<YYYYMMDDTHHMM00Z>.json`

## Audit Manifest & Failures

- **`data/raw/open_meteo/manifest.jsonl`**: Records an immutable audit log line for each successfully saved response:
  - `fetch_time_utc`: ISO 8601 UTC timestamp.
  - `source`: `"cams"` or `"weather"`.
  - `area_id`: area identifier (e.g. `central_delhi`).
  - `url`: sanitized full request URL.
  - `http_status`: HTTP status code (200).
  - `sha256`: SHA-256 digest of the raw response bytes.
  - `file_path`: path to stored JSON file.

- **`data/raw/open_meteo/failures.jsonl`**: Records any client errors (e.g., HTTP 400) or validation errors (missing `hourly.time` or requested variables). Invalid responses are never saved to the archive.
