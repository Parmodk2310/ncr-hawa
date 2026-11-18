# AGENTS.md (copy this file to the repo root as AGENTS.md)

Project: NCR Hawa, a Delhi-NCR air quality forecast (D+1, D+2) with a static-JSON web page and Android app. Owner: Pramod Kumar.
Read this file first in every session, then only the doc relevant to the current task (docs/AQ_*.md).

## What this project is
Public data in (OpenAQ stations, Open-Meteo CAMS + weather), honest forecast out (always compared with baselines), published as static JSON read by a web page and an Android app. No accounts, no ads, no personal data, no live API server.

## Hard rules
1. **Never invent numbers.** No made-up MAE, accuracy, counts, dates, station lists, licences or limits. If not measured by a script you ran, say "not measured".
2. **One task at a time.** Do not add features, refactor unrelated files, or edit docs unless asked.
3. **Plan before code.** List plan and assumptions; wait for approval before changing architecture, dependencies, data sources, splits or schemas.
4. **Show real output.** Paste the command and its result. On failure show the error and stop.
5. **No data leakage.** Features may only use data available at forecast issue time. Time-ordered splits only. Never touch the frozen test set for training or tuning.
6. **Respect data terms.** Use only approved sources (OpenAQ API with key, Open-Meteo, optionally NASA FIRMS). Never scrape other sites. Respect rate limits; keep OpenAQ calls in the backend only. Check licence flags before publishing any station data. Keep required attributions.
7. **Never default to "Good".** Missing data is `no_data`. Stale data is labelled stale.
8. **No secrets** in code, logs, URLs saved in archives, or commits. Use environment variables/CI secrets.
9. **Pin versions;** explain every new dependency in one line with its licence (flag AGPL/non-commercial).
10. **Android:** permissions limited to INTERNET and POST_NOTIFICATIONS (only when alerts are enabled). No analytics/crash/ads SDK without my approval and a policy update.
11. **Explain-back.** For leakage controls, target definition, metrics and calibration code, add why-comments and give me a plain-English explanation I can defend in an interview.
12. **No fake progress.** A task is done only when its "done when" is met and tests pass.
13. **Large raw data stays out of git** (DVC/remote).

## Conventions
Follow docs/AQ_06 (ruff, pytest, type hints, config-driven, UTC internally, IST at display). Branch `feat/A-###-name`; commits `type(scope): message`.

## Reporting back (short)
What changed (files); what you ran and real results; what is unverified or risky; suggested next task.
