# AQ_07. Task Breakdown Rules and Backlog

Status: ACTIVE

## 1. Rules
1. One task = one verifiable outcome, half a day, max one day.
2. Every task: ID `A-###`, phase, tier (MUST/SHOULD/COULD), "done when", inputs, outputs.
3. Decisions are their own tasks, before the work that depends on them.
4. Do risky tasks first (data access, licences, leakage).
5. No vague tasks ("improve model"). Write the experiment.
6. Max 3 tasks in progress. A task untouched for 14 days is cut.
7. Give the agent one task card at a time, never the whole PRD.

## 2. Task card
```
ID: A-###   Phase:   Tier:
Goal (1 sentence):
Inputs:        Outputs:
Steps:
Done when (testable):
Out of scope:
Risks/unknowns:   Estimate:
```
Agent prompt: "Read AGENTS.md and docs/<doc>. Task: <card>. First list plan and assumptions. After coding, list what you ran and real outputs. Do not invent numbers. Stop and show errors on failure."

## 3. Starting backlog

### W1: access, archive, setup
- A-001 MUST Create repo, layout, AGENTS.md, pinned env, ruff + pytest
- A-002 MUST Register OpenAQ key; fetch Delhi-NCR location list; **record each location's licence flags** (commercial, attribution, redistribution) in `data/licences.csv`
- A-003 MUST DECISION: which stations/areas to include, based on licences and data completeness
- A-004 MUST Ingest job: hourly PM2.5/PM10 (+ weather fields if available) per station, raw archived
- A-005 MUST Ingest job: Open-Meteo CAMS air-quality forecast + weather forecast for station coordinates, twice daily, raw archived with issue time
- A-006 MUST Scheduler (Actions cron) + failure alert + secret handling
- A-007 MUST Create Play developer account; note verification status (records outside repo)
- A-008 MUST Interviews x3, notes in AQ_01
- A-009 SHOULD **[VERIFY]** whether Open-Meteo offers historical forecast issuances usable for training; record result

### W2: baselines and evaluation harness
- A-010 MUST Data audit: completeness per station/hour, outliers, duplicates, negative values, flatlines
- A-011 MUST Daily target builder (IST day, completeness rule) + unit tests
- A-012 MUST CPCB PM2.5 category mapper + tests at every breakpoint (30/31, 60/61, 90/91, 120/121, 250/251) **[VERIFY breakpoints]**
- A-013 MUST Baseline B0 persistence, B1 climatology, B2 raw CAMS daily mean
- A-014 MUST Evaluation harness: MAE, RMSE, category accuracy, within-one-category, event precision/recall for Poor+, bias
- A-015 MUST Rolling-origin evaluation; frozen test season defined and hashed
- A-016 MUST Baseline results table (real numbers) in `reports/`

### W3: publish and web v0
- A-020 MUST JSON schema (AQ_13) + validator
- A-021 MUST Forecast job (baseline-only for now) writes forecast.json/status.json/accuracy.json
- A-022 MUST Static web page reading JSON; disclaimers; attribution; stale warning
- A-023 MUST Publish to static host over HTTPS
- A-024 MUST Privacy policy page live (AQ_16, minimal)
- A-025 SHOULD Hindi strings for web

### W4-5: models
- A-030 MUST Feature builder (lags, rolling means, calendar, weather forecast, CAMS forecast) with leakage test
- A-031 MUST B3 bias-corrected CAMS (linear/ridge)
- A-032 MUST Gradient boosting quantile model (10/50/90) per horizon
- A-033 MUST Event classifier or quantile-derived probability for Poor+; calibration plot
- A-034 MUST Experiment log in MLflow; compare vs baselines on validation
- A-035 MUST Frozen test evaluation; apply decision rule (AQ_12)
- A-036 MUST Error analysis: Diwali period, stubble-burning weeks, fog/inversion days, data gaps
- A-037 COULD FIRMS fire-count feature; ablation
- A-038 MUST Model card + registry record filled with real values

### W6-8: Android
- A-040 MUST App skeleton, theme, navigation
- A-041 MUST Fetch + cache JSON; stale handling; offline
- A-042 MUST Home and detail screens; baseline comparison line
- A-043 MUST About/data/attribution + disclaimer + first-run
- A-044 SHOULD Hindi/English
- A-045 SHOULD WorkManager refresh + local notification
- A-046 MUST Unit + UI tests; test on low-memory phone
- A-047 MUST Release build, signing key backup record (location only)

### W9-13: release
- A-050 MUST CI: lint, tests, schema check, eval gate
- A-051 MUST Monitoring job: daily compare forecast vs actual; publish accuracy.json
- A-052 MUST README with measured results; demo video; GitHub APK
- A-053 MUST Play listing, Data Safety, content rating, target audience, ads, access note
- A-054 MUST Closed test: 12+ testers (aim 20), log
- A-055 MUST Production application; staged rollout; daily crash/ANR check first week
- A-056 MUST Fill Model Card (AQ_12) and Resume Claims (AQ_17)
