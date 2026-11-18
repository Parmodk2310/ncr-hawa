# AQ_08. Test and QA Plan

Status: DRAFT v0.1

## 1. Test layers
| Layer | What | When |
|-------|------|------|
| Unit | Category mapper, daily aggregation, IST boundaries, completeness rule, feature builders | every PR |
| Leakage tests | Features at issue time contain no later data | every PR |
| Data validation | Schema, ranges (PM2.5 >= 0, plausible max), duplicates, timestamps monotonic | every ingest run |
| Contract | forecast.json matches schema; app and web parse it | every PR |
| Forecast evaluation | Metrics vs baselines on frozen test; prospective monitoring | every model candidate; daily live |
| App | JUnit + UI tests, offline, stale, language | every PR / release |
| Manual | Low-memory phone, slow network | every release |

## 2. Specific unit tests (must exist)
- Category boundaries at each breakpoint, both sides.
- Day boundary: reading at 23:30 IST belongs to the right day; UTC conversion.
- Completeness: day with 17 of 24 hours is rejected if rule is 18 (use your rule).
- Missing station data never becomes "Good".
- Issue-time leakage: a feature built for issue time T never reads data after T.

## 3. Forecast evaluation protocol
- Frozen test season (e.g. one full Oct-Feb winter not used in training/tuning); hash recorded.
- Rolling-origin: train on data before date d, forecast d+1/d+2, move d forward.
- Metrics per horizon: MAE, RMSE, bias; category accuracy; within-one-category; precision/recall/F1 for Poor-or-worse; Brier score if probabilistic; interval coverage (does the 10-90 interval contain truth about 80% of the time?).
- Skill score vs persistence: `1 - MAE_model / MAE_B0`.
- Report per station and overall; report worst stations.
- Slices: Diwali week, stubble-burning weeks (Oct-Nov), fog days, low-data stations.
- Statistical honesty: with few winters, differences can be noise. Report spread (e.g. bootstrap over days) and do not over-claim.

## 4. Prospective (live) evaluation
- From the first archived issuance, every forecast is stored and scored against actuals once they arrive. This is the strongest evidence. Publish it in `accuracy.json`.

## 5. App test cases
| ID | Scenario | Expected |
|----|----------|----------|
| T-01 | Airplane mode after first load | Cached data, "may be outdated" label |
| T-02 | JSON older than threshold | Stale banner |
| T-03 | JSON missing area | "No data", never "Good" |
| T-04 | Corrupt/unknown-schema JSON | Keep previous data, no crash |
| T-05 | Language switch | All strings localized |
| T-06 | Notifications denied | App works; settings explain |
| T-07 | Low-memory phone, 10 minutes use | No crash/ANR |
| T-08 | Large font setting | Layout still readable |
| T-09 | TalkBack | Category and value announced |

## 6. Pipeline failure drills
- Revoke the OpenAQ key in a test: job fails, alert fires, previous JSON stays, status shows age.
- Return malformed API data: validation stops publish.
- Run job twice: no duplicates.

## 7. Bug severity
S1: wrong "Good" shown for bad air, crash, data/privacy leak. Blocks release. S2: stale data not flagged, wrong area data, repeated sync failure. S3: UI glitches.

## 8. Release exit criteria
- [ ] S1/S2 closed; CI green; evaluation report current; disclaimers verified; closed-test feedback addressed.
