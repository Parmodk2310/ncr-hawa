# AQ_17. Admin Templates

Status: TEMPLATES

## A. README skeleton (real data only)
```
# NCR Hawa: Delhi-NCR Air Quality Forecast
One line. [Live web page] [Download APK] [Play Store link if live]
Independent project. Not an official service. Not medical advice.

## Problem and users (cited, 3 lines)
## What it does
## How accurate is it? (all measured; commands in docs/reports)
| Horizon | Model MAE | Persistence MAE | CAMS MAE | Poor+ recall (model / persistence) |
Result on frozen test season: ____. Live since ____: ____.
If the model did not beat a baseline, say so here.
## Data sources and licences (links, attribution)
## Architecture (diagram) and how to run: dvc pull && dvc repro; app build steps
## MLOps: what is automated, what is not
## Limitations (coarse CAMS grid, PM2.5-based category, sensor gaps, events)
## Privacy and safety (link to policy)
## AI assistance: built with an AI coding agent under my review; modelling and evaluation designed and verified by me. See docs/AI_Assistance_Log.
## Licence and third-party notices
```

## B. Test Report (per release)
Release/commit ____ | date ____ | tester ____ | phones (model, Android, RAM) ____ | backend/model versions ____
Planned ____ / run ____ / passed ____ / failed ____ / blocked ____
Failed cases (ID, severity, ticket) ____ | Offline/stale/Hindi results ____ | Low-memory phone result ____
Forecast evaluation summary (link) ____ | Open defects and ship/hold decision ____ | Attachments ____

## C. Forecast Export / Latency Report (replaces "model export" for this project)
JSON sizes per file (raw, gzip) ____ | app cold start and refresh time on [phone] on [network] ____ | cache hit behaviour ____ | battery impact over 24 h with background refresh ____ | stale-data behaviour tested ____

## D. Release Notes and Changelog
```
## [x.y.z] - YYYY-MM-DD
Model: model-YYYYMMDD-hash (frozen-test MAE D+1/D+2 ____, measured)
### Added  ### Changed  ### Fixed  ### Known issues
```
Play "What's new": 3 plain sentences, English + Hindi.

## E. AI Assistance Log
| Date | Task ID | What I asked | What the agent changed | What I reviewed/changed | Tests run (real output saved) | Problems found in its work |
|------|---------|--------------|------------------------|-------------------------|-------------------------------|----------------------------|

## F. Resume and Portfolio Claims Checklist
- [ ] Listed under **Projects** with real dates; no job title; no implication of employment.
- [ ] Dates/titles for past internships identical everywhere.
- [ ] Skill claims only when built and explainable:
| Skill | Add when |
|-------|----------|
| Time-series forecasting | Baselines + model evaluated with time-ordered splits, results in repo |
| Quantile regression / uncertainty | Intervals produced and coverage measured |
| Data engineering/ETL | Scheduled ingest + validation + archive running |
| DVC / MLflow | `dvc repro` works from clean clone; runs logged |
| CI/CD + eval gate | Pipeline passing; a failing case demonstrated |
| Android/Kotlin | App built and installed |
| Play Store | Only if actually published |
- Bullet pattern: "Built a Delhi-NCR PM2.5 forecast (D+1, D+2) from public station and CAMS data; on a frozen test winter it achieved __ MAE vs __ for persistence [or: did not beat persistence; documented why]; deployed as a static-JSON web page and Android app with an automated daily evaluation."
- Interview prep: leakage prevention; why persistence is hard to beat; metrics chosen; calibration; failures found; what you'd do next.
- Do not paste numbers you did not produce. Say AI-agent use openly.
