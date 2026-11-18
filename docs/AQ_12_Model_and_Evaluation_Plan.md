# AQ_12. Model and Evaluation Plan (includes Model Card, Experiment Log, Registry, Retraining, Monitoring)

Status: DRAFT v0.1. All results are blank until a script produces them.

## 1. Forecast task
For each station/area and issue time: predict the daily mean PM2.5 (IST day) for D+1 and D+2; convert to the CPCB-style PM2.5 category; give an interval and a probability of "Poor or worse".

## 2. Baseline ladder (always reported)
| ID | Baseline | Why |
|----|----------|-----|
| B0 | Persistence: tomorrow = today's daily mean | The hard-to-beat simple rule |
| B1 | Climatology: day-of-year / week-of-season average | Seasonality only |
| B2 | Raw CAMS global forecast daily mean at nearest grid cell | Free physical-model forecast (coarse, ~45 km **[VERIFIED]**) |
| B3 | Bias-corrected CAMS (linear/ridge on CAMS + recent obs) | Cheap local correction |
| M1 | Gradient boosting with lags, weather forecast, CAMS, calendar, optional fires | Main candidate |
| M2 | Optional: small sequence/neural model | Only if time permits and M1 is solid |

## 3. Decision rule (write before you see test results; edit only with a dated note)
Ship the ML forecast as "model forecast" only if, on the frozen test season:
- MAE(M1) < MAE(B0) and MAE(M1) < MAE(B2) at both horizons, overall; and
- it is not worse than B0 on Poor-or-worse recall by more than ____ (set); and
- improvement is not explained by noise (bootstrap over days; set criterion).
Otherwise: show the best-performing baseline/blend, labelled honestly ("simple forecast"), and say the ML model did not beat it. Both outcomes are reportable.

## 4. Metrics
MAE, RMSE, bias; category accuracy; within-one-category; precision/recall/F1 for Poor+ and for Very Poor+; Brier score and reliability plot for probabilities; interval coverage for the 10-90 band; skill vs B0. Per station and overall; per slice (Diwali, burning season, fog, low-data).

## 5. Training hygiene
Time-ordered splits; fixed seeds; early stopping on validation; frozen test only at the end; log config + git hash + data version for every run; class/event imbalance handled and reported (Poor+ days are the ones that matter).

## 6. Experiment Log (fill with real runs)
| Date | Run ID | Model | Change | Config | Data version | Val MAE D+1 | Val MAE D+2 | Poor+ recall | Decision | Notes |
|------|--------|-------|--------|--------|--------------|-------------|-------------|--------------|----------|-------|

## 7. Model Evaluation Report (template)
Model/version ____ | date ____ | git hash ____ | test-set hash ____ | command `____`
Tables: baselines vs model (overall, per horizon, per station); category confusion matrix; reliability plot; slices; error analysis (top 5 failures with dates and likely reasons, labelled as hypotheses); conclusion in 3 sentences; decision-rule outcome.

## 8. Model Card (template)
- Name/version ____; algorithm ____; features ____; target definition ____; training period ____; stations ____.
- Intended use: informational daily outlook for Delhi-NCR; not for health decisions or regulation.
- Not for: medical advice, school-closure decisions, legal evidence, other cities.
- Test results ____ (frozen set) and ____ (prospective since ____).
- Known failure modes: ____ (from error analysis).
- Data licences and attribution: see AQ_11.
- Ethical notes: false "Good" forecasts are harmful; conservative wording; kill switch exists.
- Update history table.

## 9. Model Version and Registry Record
| Version | Date | Run ID | Data version | Test MAE D+1 / D+2 | Beats B0? B2? | Gate result | Status (candidate/production/archived) | Rollback target |
|---------|------|--------|--------------|---------------------|---------------|-------------|----------------------------------------|-----------------|

## 10. Retraining Policy
- Schedule: retrain at the end of each season or when live MAE exceeds baseline for ____ consecutive weeks.
- Data: new archived data only after quality checks; frozen test season stays the same until a documented refresh, and baselines are rerun on any new test set.
- Gate: same decision rule; failed candidates are logged, not hidden.
- Release: update `status.json` model version; keep previous model for rollback.
- Owner: you. Review: after each season.

## 11. Monitoring Plan
See AQ_10 section 7. Additional: drift check on inputs (CAMS bias vs obs by month), station dropouts, calibration of probabilities. With few data points, say when signals are too noisy to conclude.

## 12. What you must be able to explain in interviews
Why daily mean and IST day; how leakage was prevented; why persistence is hard to beat; what quantile regression gives; how calibration was checked; what failed.
