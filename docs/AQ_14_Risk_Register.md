# AQ_14. Risk Register

Status: LIVE. Review every Sunday.

| # | Risk | Likelihood | Impact | Mitigation | Trigger |
|---|------|-----------|--------|------------|---------|
| R1 | Model cannot beat persistence/CAMS | High | Medium | Pre-written decision rule; ship honest baseline-labelled forecast; report result as a finding | Frozen-test result |
| R2 | Station licences block publishing raw station data | Medium | High | Check licences in W1; publish derived forecasts only; exclude restricted stations | Licence table |
| R3 | OpenAQ access/rate limits/changes | Medium | High | Backend-only calls, backoff, archive; fallback source only with verified terms | Job failures |
| R4 | Open-Meteo "non-commercial" interpretation or quota | Low-Med | High | Keep app free, no ads, no paid features; stay far below limits; contact them if unsure; plan paid/alternative if monetizing | Any monetization idea |
| R5 | CAMS 45 km grid too coarse to help locally | Medium | Medium | Use as feature/baseline only; evaluate honestly | B2 results |
| R6 | Missing history of forecast issuances for training | Medium | Medium | Start archiving now; train on archive; label any reanalysis-based experiments | A-009 result |
| R7 | Sensor errors, gaps, flatlines | High | Medium | QC rules, completeness thresholds, data-issues log | Audit |
| R8 | A wrong "Good" forecast on a severe day | Medium | High | Conservative wording, intervals, probability of Poor+, kill switch, never default to Good, quality incident process | Any incident |
| R9 | Users treat it as medical or official advice | Medium | High | Clear disclaimers in app, listing, policy; general health note only; no government branding | Reviews/complaints |
| R10 | Play closed test (12 testers x 14 days) fails through attrition | Medium | Medium | Recruit 20; remind testers; start early; keep a tester log **[VERIFIED rule]** | Tester count drops |
| R11 | Play launch lands after winter peak | High | Medium | Web page first; accept Play as longer-term | Timeline |
| R12 | Scope creep with other projects | High | High | Cut order in AQ_04; max 3 tasks in progress | Behind at Gate B |
| R13 | Scheduler drift/outage (Actions cron) | Medium | Medium | Stale-data banner, status.json, alerts, option to move to a VM | Missed runs |
| R14 | Overclaiming on resume | Medium | Very high | Claims checklist (AQ_17); real dates; project not job; measured numbers only | Always |
| R15 | Agent writes code you can't explain / invents numbers | High | High | Review every diff; AQ_18 rules | Any unexplained code |
| R16 | Hindi text wrong or awkward | Medium | Low-Med | Native-speaker review | Before release |
| R17 | Store listing/Data Safety mismatch with code | Medium | High | Code review per release; AQ_15 worksheet | Each release |
| R18 | Competing apps and no real users | High | Medium | Interviews; clear edge (local, honest, no ads); measure usage only via Play stats | Low installs |
| R19 | Account lockout/suspension (Play, Google, tool accounts) | Low-Med | High | 2FA, clean accounts, backups in Git, follow policies | Any warning |

Rule: a risk without a mitigation is a worry, not a plan.
