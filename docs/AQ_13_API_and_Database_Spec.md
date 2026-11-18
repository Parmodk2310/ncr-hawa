# AQ_13. API (Static JSON) and Database Specification

Status: DRAFT v0.1. There is no live API server. Clients read static files. Version the schema.

## 1. Files (base: https://<your-static-host>/v1/)
| File | Purpose | Update |
|------|---------|--------|
| status.json | health, model version, kill switch, times | every job run |
| areas.json | list of areas/stations offered | when stations change |
| forecast.json | forecasts per area | twice daily |
| accuracy.json | how past forecasts did vs baselines | daily |
| notices.json | attributions, licence notices, announcement text | when needed |

## 2. status.json
```json
{
  "schema": "1.0",
  "generated_at": "2026-01-01T06:00:00Z",
  "forecast_issued_at": "2026-01-01T05:30:00Z",
  "latest_observation_at": "2026-01-01T05:00:00Z",
  "model_version": "model-YYYYMMDD-abc123",
  "pipeline_version": "x.y.z",
  "forecast_disabled": false,
  "message_en": "", "message_hi": ""
}
```
App rule: if `forecast_disabled` is true or the file is older than a threshold, show "forecast unavailable" and keep showing last observations with their time.

## 3. forecast.json (per area)
```json
{
  "schema": "1.0",
  "issued_at": "2026-01-01T05:30:00Z",
  "areas": [
    {
      "area_id": "delhi-central",
      "name_en": "Central Delhi", "name_hi": "...",
      "now": {"pm25": 182.0, "category": "poor", "observed_at": "2026-01-01T05:00:00Z", "stations_used": 4},
      "days": [
        {"date": "2026-01-02", "horizon": 1,
         "pm25_p10": 120, "pm25_p50": 165, "pm25_p90": 230,
         "category": "very_poor", "prob_poor_or_worse": 0.82,
         "baseline_persistence": {"pm25": 182, "category": "poor"},
         "baseline_cams": {"pm25": 140, "category": "very_poor"},
         "source": "model"},
        {"date": "2026-01-03", "horizon": 2, "...": "..."}
      ]
    }
  ]
}
```
- `source`: `model` or `baseline_fallback` (shown honestly to the user).
- `category` values: `good|satisfactory|moderate|poor|very_poor|severe|no_data`.
- Missing data = `no_data`, never a default category.

## 4. accuracy.json (public honesty page)
```json
{
  "schema": "1.0",
  "window_days": 30,
  "horizon_1": {"mae_model": null, "mae_persistence": null, "mae_cams": null, "n_days": 0,
                "category_hit_rate_model": null, "category_hit_rate_persistence": null},
  "horizon_2": {"...": "..."},
  "note_en": "Based on days with complete observations only."
}
```
Numbers appear only when the evaluation job produced them.

## 5. Schema rules
Additive changes keep `schema` minor; breaking changes use `/v2/`. The app ignores unknown fields. JSON validated against a JSON Schema in CI before publishing.

## 6. Pipeline database (DuckDB/Parquet or PostgreSQL)
`stations(station_id PK, name, provider, lat, lon, licence_id, use_flag, publish_flag, first_seen, last_seen)`
`observations(station_id, ts_utc, pollutant, value, unit, source_fetch_id, quality_flag)` key `(station_id, ts_utc, pollutant)`
`fetches(fetch_id PK, source, requested_at, url_no_key, http_status, raw_path, sha256)`
`forecast_inputs(area_id, issue_ts_utc, source, target_date, variable, value)`
`forecasts(forecast_id PK, area_id, issued_at, target_date, horizon, model_version, p10, p50, p90, category, prob_poor_plus, source)`
`daily_actuals(area_id, date, pm25_mean, hours_valid, valid)`
`scores(forecast_id, actual, abs_error, category_hit, scored_at)`
`model_versions(version PK, registered_at, run_id, test_metrics_json, status, notes)`
Indexes on `(station_id, ts_utc)`, `(area_id, target_date)`. Raw payloads kept in files, referenced by `fetches`.

## 7. Retention
Raw archive: keep (small, scientific value) **[check source licences allow keeping]**. Logs: set days. Published JSON: current + dated copies for audit.
