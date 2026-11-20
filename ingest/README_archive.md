# Open-Meteo Forecast Archive

This directory contains ingestion tooling to periodically archive CAMS global air quality forecasts and numerical weather prediction forecasts for Delhi-NCR monitoring points.

## Important Note on "Issue Time"

The Open-Meteo API response does not report the exact meteorological model run/cycle time (e.g., 00Z or 12Z CAMS initialization). 

Therefore, in our data pipeline:
- We record and treat the **fetch timestamp in UTC** as the **"issue time"** for the archived issuance.
- We do **not** claim or infer the meteorological model run time.
- All downstream features must strictly rely on this fetch timestamp to prevent data leakage (features only use issuances fetched prior to forecast target days).

## Weather Model Pinning (WP1)

* **Pinning Date**: 2026-11-20
* **Commit**: `feat(ingest): pin weather models and archive status (WP1)`
* **Primary Weather Model**: `ecmwf_ifs025` (ECMWF IFS 0.25° global model, chosen for superior atmospheric physics and explicit Boundary Layer Height support).
* **Secondary Weather Model**: `ncep_gfs_seamless` (NOAA GFS global model, archived as a secondary source and cross-model comparison).
* **Earlier Archives**: Weather files archived prior to this commit (located in `data/raw/open_meteo/weather/`) were fetched using Open-Meteo's default model (`models=auto`). These older files remain untouched for historical auditability.

## Raw Storage Layout

Raw payloads are stored under `data/raw/open_meteo/`:
- `data/raw/open_meteo/cams/<area_id>/<YYYYMMDDHHMM00Z>.json`
- `data/raw/open_meteo/weather_ecmwf/<area_id>/<YYYYMMDDHHMM00Z>.json` (pinned primary ECMWF)
- `data/raw/open_meteo/weather_gfs/<area_id>/<YYYYMMDDHHMM00Z>.json` (pinned secondary GFS)
- `data/raw/open_meteo/weather/<area_id>/<YYYYMMDDHHMM00Z>.json` (legacy default model archives)

## Audit Manifest & Failures

- **`data/raw/open_meteo/manifest.jsonl`**: Records an immutable audit log line for each successfully saved response:
  - `fetch_time_utc`: ISO 8601 UTC timestamp.
  - `source`: `"cams"` or `"weather"`.
  - `area_id`: area identifier (e.g. `central_delhi`).
  - `model`: model string (e.g. `"ecmwf_ifs025"`, `"ncep_gfs_seamless"`, or `"default"`).
  - `request_url_has_models`: boolean indicating whether the `models` query parameter was passed in the request URL.
  - `url`: sanitized full request URL.
  - `http_status`: HTTP status code (200).
  - `sha256`: SHA-256 digest of the raw response bytes.
  - `file_path`: path to stored JSON file.

  *Note*: Pre-WP1 manifest lines omit `model` and `request_url_has_models`; consumers treat missing values as `"default"` and `False` respectively.

- **`data/raw/open_meteo/failures.jsonl`**: Records any client errors (e.g., HTTP 400), server errors, or validation errors (missing `hourly.time` or requested variables). Invalid responses are never saved to the archive.

## Archive Health Monitoring

The script `scripts/status_archive.py` reads `manifest.jsonl` and reports:
1. **Runs per day**: Grouped by UTC date, where fetches within 10 minutes are clustered into one run.
2. **Hours between consecutive runs**: Time elapsed between runs.
3. **GAP alerts**: Any interval between consecutive runs exceeding 7.0 hours is flagged `[GAP]`.
4. **Age of last fetch**: Elapsed hours since the most recent fetch timestamp.
5. **File counts and storage size**: Total files recorded and total size in MB on disk.

Usage:
```bash
python scripts/status_archive.py --manifest data/raw/open_meteo/manifest.jsonl
```
