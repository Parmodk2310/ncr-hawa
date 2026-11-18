# AQ_09. Security and Privacy Review Checklist

Status: DRAFT. Tick only what you verified.

## 1. Secrets
- [ ] OpenAQ key and FIRMS key only in CI secrets/environment; never in repo, logs, or client apps.
- [ ] Secret scanning on; `.env` ignored; `.env.example` provided.
- [ ] Keys can be rotated; rotation steps written (AQ_10).
- [ ] Android keystore and passwords outside repo and outside the AI agent's folder; backed up in two places.

## 2. Data pipeline
- [ ] Source terms re-checked; rate limits respected; backoff on errors.
- [ ] No scraping of sites without terms permission.
- [ ] Raw archive does not contain secrets (strip keys from stored URLs/headers).
- [ ] Publish step writes only the allowed public fields; licence-restricted data not republished.
- [ ] CI workflows use least-privilege tokens; third-party actions pinned.

## 3. Hosting and JSON
- [ ] HTTPS only; no mixed content.
- [ ] Static files contain no private data.
- [ ] Cache headers sensible; stale-data detection works.
- [ ] Hosting access logs: who can read them; retention known (privacy policy states it).

## 4. Android
- [ ] Permissions: INTERNET, POST_NOTIFICATIONS only (if alerts exist). No location, no contacts, no storage.
- [ ] Cleartext traffic disabled.
- [ ] No analytics/ads/crash SDKs unless declared in Data Safety and policy.
- [ ] `debuggable=false`; no debug logs with data.
- [ ] Dependencies scanned; licences listed.
- [ ] No keys hard-coded (anything in an APK can be extracted).

## 5. Integrity and trust
- [ ] JSON schema validated before publish; app validates before display.
- [ ] Optional: sign or checksum the forecast file so a tampered file is detectable **[consider; decide]**.
- [ ] Account/credential protection: 2FA on GitHub, hosting, Play Console, Google account.
- [ ] Branch protection on `main`; no force pushes.
- [ ] A malicious or wrong forecast (e.g. "Good" on a Severe day) is a harm. Have a kill switch: `status.json` can set `forecast_disabled: true`, and the app then shows "forecast unavailable".

## 6. Privacy
- [ ] No personal data collected by the app or pipeline. Confirm by code review each release.
- [ ] Tester list and contact details stored outside the repo.
- [ ] Policy matches the code (AQ_16).
- [ ] India's DPDP Act, 2023: understand obligations if any personal data is ever processed. **[VERIFY with official text; not legal advice.]**

## 7. Operations
- [ ] Alerts for failed jobs and stale data.
- [ ] Backups of the archive; one restore tested.
- [ ] Incident steps written (AQ_10).

## 8. Licences
- [ ] Open-Meteo attribution shown; free tier kept non-commercial **[VERIFIED terms; confirm your use]**.
- [ ] OpenAQ per-station licence flags checked for any published data.
- [ ] AGPL or share-alike components identified and handled (Open-Meteo server code is AGPL but you only use the API; check any library you add).

## 9. Sign-off
Reviewer: ____ Date: ____ Open findings: ____
