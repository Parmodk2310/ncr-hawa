# AQ_06. Engineering Standards

Status: ACTIVE (applies to you and to Antigravity)

## 1. Python
- Pin Python and dependency versions (lockfile). `ruff` format/lint, `pytest`, type hints on public functions.
- Notebooks only for exploration; real logic in packages with tests.
- Config-driven (YAML), seeds logged, no hard-coded paths or keys.
- All time handling in UTC internally; named constants for IST conversion; unit tests for day-boundary logic.

## 2. Data engineering
- **Raw data is immutable.** Save each API response as received, with fetch time, URL (without key), and status code.
- Idempotent jobs: running twice does not duplicate rows.
- Respect rate limits and terms; use backoff; identify your app in the User-Agent where allowed.
- Schema validation (e.g. pydantic/pandera) at every boundary; a failed validation stops publishing.
- Never invent or silently fill values. Imputation (if any) is documented, flagged in a column, and never used in evaluation targets.

## 3. Modelling rules
- Time-ordered splits only; test set frozen and hash recorded.
- No feature may use information after the issue time. Write a leakage test.
- Every model compared to baselines B0-B2 (AQ_12) on the same data and metrics.
- Report with fixed seeds, config, git hash, data version.

## 4. Android (Kotlin)
- Compose + MVVM, coroutines, no network or disk on main thread, ktlint.
- Strings in resources (English/Hindi). No hard-coded URLs/keys (the JSON URL is public, not a secret).
- No analytics/crash SDK in MVP unless added to the Data Safety form and privacy policy.
- Least permissions: INTERNET, POST_NOTIFICATIONS (requested only when needed).

## 5. Git
- Branch per task: `feat/A-014-baseline-eval`. Small PRs. Commit style `type(scope): message`.
- `main` always green. Never commit: secrets, keystores, large raw data, `.env`.
- Tag releases `vX.Y.Z`.

## 6. Honesty rules for metrics
- Metric valid only with: frozen test set, fixed split rule, config + commit hash, command recorded.
- Never tune on the test set. Never copy numbers from other apps, papers or blogs into your results.
- Report where the model is worse than baseline.

## 7. Definition of Done
- [ ] Runs from a clean checkout.
- [ ] Tests added/updated and pass; lint passes.
- [ ] Docs updated if behaviour changed.
- [ ] No secrets or large files in git.
- [ ] You can explain every line.

## 8. Using the AI agent
You review every diff. Anything you cannot explain does not merge. The agent never reports numbers you did not reproduce. Log sessions (AQ_17).
