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

## Archive Health Monitoring (WP1, WP2b, WP2c)

The script `scripts/status_archive.py` reads `manifest.jsonl` and reports:
1. **Runs per day & time span**: Grouped by UTC date, where fetches within 10 minutes are clustered into one run. Each run reports its start and end UTC timestamps: `Run <id> (<start_utc> -> <end_utc>): <count>/<expected> files`.
2. **Completeness per clustered run**:
   - **Current Runs**: Expected files = $\text{areas} \times (1\text{ CAMS} + \text{configured weather models})$ (e.g., $5 \times (1 + 2) = 15$ files).
   - **Legacy Runs (`[LEGACY LAYOUT]`)**: Runs where no entry contains a `model` field (pre-pinning) expect $\text{areas} \times 2$ files (`cams` + default `weather`). These are labelled `[LEGACY LAYOUT]` instead of `[INCOMPLETE]`.
   - **Target-level auditing**: A run is never flagged `[INCOMPLETE]` when `files >= expected` unless a named target is actually missing. Only missing targets are reported.
3. **Hours between consecutive runs & GAP alerts**: Time elapsed between runs. Any interval exceeding 7.0 hours is flagged **`[GAP]`**.
4. **Age of last fetch**: Elapsed hours since the most recent fetch timestamp.
5. **File counts and storage size**: Total files recorded and total size in MB on disk.
6. **Execution log audit (`--log <run.log>`)**: Scans execution logs to ensure clean job completion. Any `start` line lacking a matching `exit=` line before the next `start` or EOF is flagged **`[START WITHOUT EXIT]`**.
7. **Date filtering (`--since <YYYY-MM-DD>`)**: Ignores manifest entries older than the specified UTC date.
8. **Merged cross-archive audit (`--merge <path>`)**: Combines two manifests (e.g. local laptop and GitHub Actions `archive-data`), de-duplicates entries by `(area_id, source, model, fetch_time_utc)`, and checks every 6-hour UTC cycle window (`00:00`, `06:00`, `12:00`, `18:00`) since `--since`. Any cycle with zero data across both sources is flagged **`[NO DATA]`**.

Usage:
```bash
# Basic check
python scripts/status_archive.py --manifest data/raw/open_meteo/manifest.jsonl --log run.log

# Filter recent runs since a given date
python scripts/status_archive.py --manifest data/raw/open_meteo/manifest.jsonl --since 2026-11-20

# Dual-manifest audit merging local and actions archives
python scripts/status_archive.py --manifest data/raw/open_meteo/manifest.jsonl --merge archive-data/manifest.jsonl --since 2026-11-20
```

## GitHub Actions Automated Archive (WP2, WP2b)

### How It Works
Automated scheduled archiving is managed by the GitHub Actions workflow at `.github/workflows/archive.yml`:
- **Schedule**: Runs 4 times daily at `01:17`, `07:17`, `13:17`, and `19:17` UTC (odd minutes to avoid top-of-hour queue contention). It also supports manual on-demand execution via `workflow_dispatch`.
- **Job Guardrails**: A job timeout of `timeout-minutes: 10` prevents hanging runner jobs.
- **Note on Timing**: Scheduled runs on GitHub Actions can start late depending on runner queue delays; exact wall-clock timing is not guaranteed.
- **Orphan Branch Storage**: Raw data **never** touches `main`. The workflow maintains a completely separate, orphan branch named `archive-data`. The workflow checks out `main` into the runner root, checks out (or initializes) `archive-data` into a subfolder `archive-data/`, and executes `python -m ingest.archive_open_meteo --raw-dir archive-data`.
- **Security & Bot Identity**: Authentication uses a step-level environment variable `GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}` rather than exposing tokens in git command arguments or URLs. Commits on `archive-data` are authored by the standard bot identity:
  - Name: `github-actions[bot]`
  - Email: `41898282+github-actions[bot]@users.noreply.github.com`
- **Failure Resilience & Reporting**: If any fetch request fails, the archive script exits with a non-zero exit code so the GitHub Actions job turns red. However, the commit and push step runs with `if: always()`, ensuring partial data and failure records (`failures.jsonl`) are preserved on `archive-data`. A final step (`if: always()`) reports the exact number of committed files and prints `git log -1 --stat` for the archive branch.
- **Concurrency**: Governed by concurrency group `archive-open-meteo` with `cancel-in-progress: false` to prevent overlapping runs.

### How to Disable It
- **Via GitHub Web UI**: In the repository on GitHub, navigate to **Actions** -> select the **Scheduled Open-Meteo Forecast Archive** workflow in the left sidebar -> click the three dots menu (`...`) on the right -> select **Disable workflow**.
- **Via Git**: Comment out or delete the `schedule:` trigger block in `.github/workflows/archive.yml` and commit/push to `main`.

### Dual Independent Archives & De-duplication
Forecasts may be collected independently by two distinct sources:
1. **Local Archive**: Manual or local runs on a developer laptop (stored under `data/raw/open_meteo/`).
2. **Actions Archive**: Cloud runs on GitHub Actions (stored in the orphan branch `archive-data`).

Because both archives write immutable raw JSON payloads and log an audit record containing the `sha256` hash of the response bytes in `manifest.jsonl`, downstream consolidation tools can safely de-duplicate files across both archives using their SHA-256 digest and fetch timestamps without risk of duplicate training rows or data contamination.

