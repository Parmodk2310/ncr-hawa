# AQ_03. Technical Architecture

Status: DRAFT v0.1

## 1. Overview
```
 OpenAQ (obs)   Open-Meteo (CAMS + weather)   NASA FIRMS (optional)
      |                  |                           |
      v                  v                           v
   ingest jobs (Python, scheduled: GitHub Actions cron or small VM)
      |  raw responses archived (immutable, dated)
      v
   Parquet/DuckDB store  --DVC-->  remote storage
      |
      v
   feature build -> baselines + model -> forecast job (twice daily)
      |                                   |
      |                       evaluation job (daily, vs actuals)
      v                                   v
   publish static JSON  (forecast.json, status.json, accuracy.json)
      |                                   
 static host (HTTPS, CDN)  <---- web page (static) 
      ^
      |  fetch JSON
   Android app (Compose) + WorkManager (refresh, local notification)
```
Key idea: **no live server and no user data.** Clients only download public JSON. This avoids OpenAQ rate-limit/CORS problems (their FAQ says clients must go through your own backend **[VERIFIED]**), cuts cost, and shrinks the privacy surface.

## 2. Components and decisions
| Area | Choice | Why | Alternative |
|------|--------|-----|-------------|
| Language | Python 3.x for data/ML | Your strength | - |
| Storage | Raw JSON/CSV + Parquet, DuckDB for queries | Simple, cheap, reproducible | PostgreSQL later |
| Versioning | DVC (data) + Git (code) | Reproducibility | - |
| Tracking | MLflow or W&B (pick ONE) | Experiments | - |
| Models | Baselines, then gradient boosting (e.g. LightGBM-style) with quantile outputs; optional small neural net | Strong for tabular time series; interval forecasts | Linear/ridge bias-correction |
| Scheduler | GitHub Actions cron | Free for public repos; **[VERIFY limits]**; may drift by minutes | Small VM + cron |
| Hosting (JSON + web) | Static host with HTTPS (GitHub Pages / Cloudflare Pages / object storage) | Free tiers **[VERIFY]** | - |
| Android | Kotlin, Jetpack Compose, WorkManager, Room or DataStore for cache, Retrofit/Ktor | Native notifications and offline cache | PWA + TWA (less native control) |
| CI | GitHub Actions: lint, tests, schema checks, eval gate | | |

ADR-001 (Android native vs PWA/TWA): choose native Compose for offline cache and local notifications. Trade-off: more code. Review if Week 6 progress is slow; fall back to web page only.

## 3. Time and units
- Store all timestamps in UTC; convert to IST (Asia/Kolkata) only at display.
- Daily target = mean of valid hourly values over the **IST calendar day** (decide and document one definition; CPCB-style 24-h averaging uses a defined window **[VERIFY]**).
- Require a minimum data completeness (e.g. at least 18 of 24 hourly values; set number and document) for a daily value to count.

## 4. Forecast definition
- Target: station (or area-aggregate) daily mean PM2.5, D+1 and D+2.
- Output: median + interval (e.g. 10th and 90th percentile), derived category from median, probability of "Poor or worse" from a classifier or from quantiles.
- Issue times: shortly after each CAMS update (CAMS global is updated every 12 hours **[VERIFIED]**); store the issue time with each forecast.
- Area aggregation rule: documented; compare "per station" and "area mean" in evaluation.

## 5. Leakage controls (critical)
- Features use only data available at issue time. Weather and CAMS values are *forecast* values issued before the target day, **never** analysis/reanalysis values for the target period.
- Historical CAMS/weather *forecast issuances* may not be fully available for training. **[VERIFY Open-Meteo historical forecast availability.]** If not, start archiving now and train on the archive; use reanalysis only with clear labelling and never for evaluation.
- Time-ordered splits only. No random split.

## 6. Failure handling
| Failure | Behaviour |
|---------|-----------|
| OpenAQ down / key invalid | Keep last observations, mark stale, alert you |
| CAMS call fails | Use forecast without CAMS feature (fallback model) and mark it |
| Too few valid stations | Publish "insufficient data", not a guess |
| Publish step fails | Previous JSON remains; status.json shows age |
| Schema change in source | Validation fails the job; previous JSON stays |

## 7. Security and privacy architecture
- API keys only as CI secrets / environment variables. Never in client apps or repo.
- Clients never call OpenAQ; only your static JSON.
- No user identifiers. Hosting logs are the hosting provider's (state this in the privacy policy).

## 8. Repo layout
```
ncr-hawa/
  AGENTS.md  README.md  docs/
  ingest/  features/  models/  evaluate/  publish/
  web/  android/
  data/ (DVC)  configs/  tests/  .github/workflows/
```
