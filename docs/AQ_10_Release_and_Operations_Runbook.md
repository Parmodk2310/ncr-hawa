# AQ_10. Release and Operations Runbook

Status: DRAFT v0.1

## 1. Versions
- App `MAJOR.MINOR.PATCH`; model `model-YYYYMMDD-<hash>`; data pipeline version in `status.json`.
- Every forecast file records model version and issue time.

## 2. Daily operation (automated)
1. Hourly: ingest observations. 2. Twice daily (after CAMS updates): ingest forecasts, build features, issue forecast. 3. Daily: score yesterday's forecasts vs actuals, update `accuracy.json`. 4. Alert you on any failure.

## 3. Publishing a model (gate)
Promote only if the frozen-test and prospective results satisfy the decision rule in AQ_12. Record in the registry table. Keep the previous model for instant rollback.

## 4. Web release
Build static page -> deploy -> smoke test (opens, shows data, shows stale banner when forced) -> record version.

## 5. App release checklist
1. Freeze scope; branch; version name/code; tag.
2. Test on 2-3 phones including low-memory; offline; denied permissions; Hindi.
3. Remove debug logs/keys; verify permissions list.
4. Build signed .aab; check target API level **[VERIFY requirement]**, size.
5. Back up signing key location record (never the key).
6. Upload to closed track first. Release notes in English + Hindi.
7. After closed test: apply for production; staged rollout 10-20%, then expand; watch Android vitals daily first week.

## 6. Rollback
- Bad forecast: set `forecast_disabled: true` in `status.json` (app shows "forecast unavailable"), then roll model back.
- Bad web deploy: redeploy previous tag.
- Bad app build: halt rollout in Play Console, publish fixed patch (an installed app keeps old code until users update, so the JSON kill switch matters).
- Log every rollback and reason in `CHANGELOG.md`.

## 7. Monitoring plan (what you actually look at)
| Signal | Source | Frequency | Action |
|--------|--------|-----------|--------|
| Ingest success / data completeness | job logs | daily | investigate gaps |
| Forecast age | status.json | alert if older than X hours (set) | check scheduler |
| Live MAE/bias vs baseline | accuracy.json | weekly | trigger review if model worse than baseline for N weeks (set N) |
| Station dropouts | ingest stats | weekly | remove or flag station |
| Calibration of "Poor+" probability | accuracy.json | monthly | recalibrate |
| Crashes / ANR | Play Console | daily first week, then weekly | fix, halt rollout |
| Hosting/API quota | provider dashboards | monthly | stay under free-tier limits |

## 8. Incidents
1. Detect (alert, user report). 2. Contain (kill switch). 3. Fix/rollback. 4. Post-mortem in `docs/incidents/`: what, why, fix, prevention.
Special case: a forecast that said "Good/Satisfactory" for a day that turned Poor or worse is a quality incident; record it and look for a pattern.

## 9. Secrets rotation
OpenAQ/FIRMS keys: rotate if leaked or every few months; update CI secret; verify job; revoke old key.

## 10. Backups
Archive and database: periodic export to a second location; test one restore.

## 11. Housekeeping
Monthly dependency review; yearly licence re-check (Open-Meteo, OpenAQ); check Play policy changes before each release.
