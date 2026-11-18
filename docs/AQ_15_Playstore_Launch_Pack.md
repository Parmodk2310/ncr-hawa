# AQ_15. Play Store Launch Pack (45-item tracker, listing, declarations, closed test)

Status: DRAFT. Play Console form names, image sizes and policy details are from memory unless marked. **Confirm in Play Console and the official policy pages.**

## 0. Verified rule
Personal developer accounts created after Nov 13, 2023 must run a closed test with at least 12 testers opted in continuously for 14 days before applying for production access **[VERIFIED 2026-11-15, Google Play Help]**. Internal and open tests do not count (secondary source) **[VERIFY]**. Organization accounts are widely described as exempt but need business verification (D-U-N-S) that can take weeks **[secondary, VERIFY]**. Over-recruit (20 testers) because attrition is the usual failure.

## 1. Document tracker (45 items)
Status: DONE = file exists, TEMPLATE = fill with real data, TODO = after the thing exists.

### Project (11)
| Item | File | Status |
|------|------|--------|
| Problem Statement and Scope | AQ_01 | DONE (fill interviews) |
| PRD | AQ_02 | DONE |
| System Architecture | AQ_03 | DONE |
| API Specification | AQ_13 (static JSON; add JSON Schema file when coded) | DONE |
| Database Schema | AQ_13 | DONE |
| Test Plan | AQ_08 | DONE |
| Test Report | AQ_17 | TEMPLATE |
| Risk Register | AQ_14 | DONE |
| README | AQ_17 | TEMPLATE |
| Release Notes and Changelog | AQ_17 | TEMPLATE |
| AI Assistance Log | AQ_17 | TEMPLATE |

### Data/ML/Ops (11)
| Item | File | Status |
|------|------|--------|
| Dataset Datasheet | AQ_11 | TEMPLATE |
| Dataset Source and Licence Record | AQ_11 | TEMPLATE + verified findings |
| Data Quality/Labelling Guideline | AQ_11 | DONE |
| Experiment Log | AQ_12 | TEMPLATE |
| Model Evaluation Report | AQ_12 | TEMPLATE |
| Model Card | AQ_12 | TEMPLATE |
| Forecast Export/Latency Report (JSON size, app load time on low-end phone) | AQ_17 | TEMPLATE |
| Model Version and Registry Record | AQ_12 | TEMPLATE |
| Monitoring Plan | AQ_10, AQ_12 | DONE |
| Deployment and Rollback Runbook | AQ_10 | DONE |
| Retraining Policy | AQ_12 | DONE |

### Play assets (16)
| Item | Where | Status |
|------|-------|--------|
| Developer Account Verification Records | section 2 | TEMPLATE (locations only) |
| Closed Testing Tester List and Log | section 3 | TEMPLATE |
| .aab | build | TODO |
| Signing Key Backup Record | section 4 | TEMPLATE |
| Target API Level Check | section 5 | TEMPLATE |
| Store Listing Text | section 6 | DRAFT |
| App Icon 512x512 | design | TODO (own design) |
| Feature Graphic 1024x500 | design | TODO |
| Phone Screenshots | app | TODO |
| Data Safety Answers | section 7 | WORKSHEET |
| Content Rating Answers | section 8 | WORKSHEET |
| Target Audience Declaration | section 9 | DRAFT |
| Ads Declaration | section 10 | DRAFT |
| App Access Instructions | section 11 | DRAFT |
| Permissions Declaration | section 12 | DRAFT |
| Account/Data Deletion Page | AQ_16 | DRAFT (no accounts in MVP; still publish a data-request page) |

### Legal/privacy (7), all in AQ_16
Privacy Policy, Terms of Use, Not-Official-Service and Not-Medical-Advice Disclaimer, User Consent Text, Personal Data Handling Note, Data Retention and Deletion Policy, Third-Party Licence List.

## 2. Developer Account Verification Records
Do NOT keep ID scans or card numbers in the repo.
| Item | Where kept | Status | Date |
|------|-----------|--------|------|
| Account type (personal/org) | | | |
| Registration fee paid **[VERIFY amount]** | receipt location | | |
| Identity verification | | | |
| Contact details verified | | | |
| Developer page details | | | |

## 3. Closed Testing Tester List and Log
Needs 12+ opted in for 14 continuous days; aim 20.
| # | Tester (initials) | Phone/Android | Opted in (date) | Still opted in? | Feedback |
|---|-------------------|---------------|-----------------|-----------------|----------|
Full contact list outside the repo. Log: date, build, issue, severity, fixed in, screenshot link.
Recruiting ideas: family, friends, colleagues, college groups, local residents' groups; people who actually live in Delhi-NCR give the most useful feedback. Do not buy or fake testers (policy violation risk).

## 4. Signing Key Backup Record (locations only)
Play App Signing used? ____ **[VERIFY how upload/app signing keys work now]** | Keystore location 1 ____ | location 2 ____ | passwords in password manager ____ | alias ____ | recovery steps ____ | never in repo/agent folder.

## 5. Target API Level Check
Required target API today ____ **[VERIFY on Play policy page]** | targetSdk ____ | compileSdk ____ | minSdk ____ (choose using real device share data) | checked on ____.

## 6. Store Listing Text (draft)
Name options: **NCR Hawa: Air Forecast** / **Delhi NCR Air Forecast** (no "official", "CPCB", "government"). **[VERIFY name/short/full description length limits.]**
Short: See tomorrow's air quality outlook for Delhi-NCR, with honest accuracy.
Full (draft):
NCR Hawa shows a simple outlook for air quality in Delhi-NCR for today, tomorrow and the day after. It uses public air-quality and weather data and shows how its forecast compares with simple guesses, so you can judge how much to trust it.
- Today, tomorrow and day-after outlook for your area
- Chance of Poor or worse air
- Shows how recent forecasts performed
- Works with saved data when you are offline
- Hindi and English
- No ads, no sign-up
Important: This is an independent app. It is not an official government service and is not affiliated with any government body. Forecasts can be wrong. Information here is general and is not medical advice. Data sources and licences are listed inside the app.
(Do not state accuracy figures in the listing until measured and stable; if you do, they must match accuracy.json and the date.)

## 7. Data Safety Worksheet
Fill from code review each release.
| Data type | Collected by app? | Shared? | Notes |
|-----------|------------------|---------|-------|
| Precise/approx location | No (area picker only) | - | Add "Use my location" later only with policy/form update |
| Personal info | No | - | |
| Photos/files | No | - | |
| Device or other IDs | No (verify libraries) | - | |
| App activity/analytics | No (no analytics SDK) | - | |
| Crash logs | **[VERIFY]** depends on libraries; Play's own Android vitals are separate | | If any crash SDK is added: declare |
Also record: encryption in transit (HTTPS) **[confirm what the form asks]**; deletion path (no user data held); privacy policy URL. **Answers must match the code and policy.** Check every dependency for hidden data collection.

## 8. Content Rating Worksheet
Expected: no violence, sexual content, gambling, user chat or user-generated content. Health information category: **[VERIFY whether the questionnaire or a Health apps declaration applies to apps with health advice]**. Record answers and date.

## 9. Target Audience
Adults (18+) recommended **[VERIFY form options]**; not designed for children even though parents may use it.

## 10. Ads Declaration
No ads. (Keeps Open-Meteo non-commercial use clearer and Data Safety simpler.)

## 11. App Access Instructions for Reviewers
```
No login required. Open the app, choose an area, and view the forecast.
The app needs internet to refresh data; it shows saved data offline.
Notifications are optional (Settings > Alerts).
Contact: <email>
```

## 12. Permissions Declaration
| Permission | Why | When requested |
|------------|-----|----------------|
| INTERNET | Download forecast JSON | normal |
| POST_NOTIFICATIONS | Optional daily alert | only when user turns on alerts |
| Location / camera / storage / contacts | **Not used** | - |

## 13. Pre-submission checklist
- [ ] Policy, Data Safety and code match; disclaimer visible in app and listing
- [ ] Privacy policy URL opens without login
- [ ] .aab signed; versionCode higher than previous uploads
- [ ] Pre-launch report reviewed; crash-free on 2-3 phones
- [ ] Hindi reviewed by a native speaker
- [ ] Attributions shown (Open-Meteo, CAMS, OpenAQ/source providers)
- [ ] Production-access answers prepared: how you recruited testers, feedback received, fixes made

## 14. Launch order
Closed test -> production access application -> staged rollout 10-20% -> expand -> watch crashes/ANR daily for a week -> add Play link to README -> demo video -> resume with measured numbers only.
