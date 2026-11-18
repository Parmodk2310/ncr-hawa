# AQ_04. Phase Plan

Status: DRAFT v0.1 | Today: Sunday 2026-11-15 | Start: Monday 2026-11-16
Assumes ~15 hours/week. If you have other commitments (job search, other projects), stretch it. Do not pretend.

## Honest timeline note
The Play closed test alone needs 12 testers opted in for 14 continuous days **[VERIFIED 2026-11-15, Google Play help]**, for personal accounts created after Nov 13, 2023. Add build time, review and staged rollout: **the Play app will likely arrive around February 2027, near the end of the Delhi winter.** So: real users get the **web page** this winter; Play is the longer-term release.

## Dated plan
| Week (starts) | Work | Exit criteria |
|---------------|------|---------------|
| W1 (Nov 16) | Verify data access + licences; create Play developer account (start verification); start **archiving** forecasts and observations daily; repo + AGENTS.md; 3 interviews | OpenAQ key works; licence table filled; archive job runs 3 days |
| W2 (Nov 23) | Data audit; PM2.5 daily target; baselines B0-B2 + evaluation harness | Baseline table on a historical period |
| W3 (Nov 30) | Forecast job + JSON schema + **web page v0** (baseline forecasts, honest labels) | Live URL with real users (family, friends, interviewees) |
| W4-5 (Dec 7) | Models (bias-corrected CAMS, gradient boosting with quantiles), tuning on validation | Experiment log; candidate model |
| W5 (Dec 14) | Frozen test evaluation; decision rule applied; model card | Evaluation report |
| W6-8 (Dec 21) | Android app (area picker, forecast, offline cache, notice, Hindi); privacy policy live | Stable build; Gate B |
| W8 (Jan 4) | **Recruit 12+ testers (aim 20) and start closed test** | Testers opted in |
| W9-10 (Jan 11) | CI/eval gate, monitoring, README, demo video, GitHub APK | MUST items done |
| W10-11 (Jan 18) | Closed test completes (14 days continuous); fix bugs; Play forms | Production access applied |
| W12-13 (Feb 1) | Staged rollout 10-20% then up; watch crash/ANR | Live or decision to stay web-only |
| Buffer | 2-3 weeks of slack; do not count as free | |

## Gates
- **Gate A (end W2):** baseline evaluation exists. If data is too sparse or licences block use, rescope or stop.
- **Gate B (end W8):** stable build, privacy policy live, 12+ testers committed.
- **Gate C (before production):** Data Safety matches the code; closed test finished; no S1/S2 bugs; evaluation page honest.

## Weekly ritual (Sunday, 15 min)
What shipped, what slipped, what to cut. Update this file. Delete tasks untouched for 14 days.

## Cut order when late
1. Fire feature, map, widget. 2. Hindi polish (keep English). 3. Notifications. 4. Play production (stay on web + GitHub APK).
Never cut: data archive, baselines, honest evaluation, disclaimers.
