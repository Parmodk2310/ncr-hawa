# AQ_16. Legal and Privacy Pack

Status: DRAFTS, NOT LEGAL ADVICE. Fill `[BRACKETS]`. Make sure every statement is true of your code. Have a knowledgeable reviewer check before launch. India's Digital Personal Data Protection Act, 2023 may apply if you ever process personal data; **verify current status and rules from official sources.** The MVP is designed to collect none.

---
## A. Privacy Policy (publish on a public web page, English + Hindi)
**NCR Hawa Privacy Policy** | Updated: [DATE] | Contact: [EMAIL] | Developer: [NAME], [CITY, STATE], India

1. **What the app does.** It shows an air-quality outlook for areas in Delhi-NCR using public data.
2. **What we collect.** The app does not ask you to create an account and does not collect your name, phone number, email, contacts, photos, or location. Your chosen area and settings are stored on your phone only.
3. **Notifications.** If you turn on alerts, the app schedules them on your phone. We do not send your device identifiers to us for this. [Confirm true: no FCM.]
4. **Technical data.** When the app or website downloads forecast files, the hosting provider [NAME, COUNTRY] may log technical details such as IP address and time in ordinary server logs. We [do not access/can access] these logs and keep them for [X days]. [Fill from the real host.]
5. **No selling or ad sharing.** We do not sell data and the app has no ads. [Add any third-party SDK here if you ever add one.]
6. **Third-party data.** Forecasts are made from public data sources listed in the app (About > Data sources).
7. **Children.** The app is intended for adults and is not directed at children.
8. **Your choices.** You can clear app data or uninstall at any time. If you contact us, we use your message only to reply [and delete it after X days].
9. **Security.** Files are downloaded over HTTPS. No system is perfectly secure.
10. **Changes.** We will update this page and date when practices change.
11. **Contact/complaints.** [EMAIL]. [Add grievance contact if required **VERIFY**.]

---
## B. Terms of Use (short)
1. Free, provided "as is", no warranty. Forecasts may be wrong or unavailable.
2. Information is general, not medical or professional advice. Do not rely on it for emergency, medical or safety decisions.
3. Not an official service; not affiliated with any government body or data provider.
4. Data from third parties is subject to their terms and attribution (see About).
5. Do not misuse the service or overload it (no scraping the forecast files at high frequency).
6. We may change or stop the service.
7. To the extent permitted by law, the developer is not liable for losses from use. [Lawyer to check enforceability.]
8. Governing law India; [jurisdiction]. [Review.] Contact: [EMAIL].

---
## C. Disclaimers (show in app first run, About, listing, README, website)
> NCR Hawa is an independent app by an individual developer. It is **not** an official government service and is not connected to, endorsed by, or operated by any government body or air-monitoring agency. Forecasts are statistical estimates and can be wrong. The health notes are general information and **not medical advice**; if you feel unwell or have a medical condition, speak to a doctor. For official air-quality information, visit the relevant government sources.
> The category shown is based on PM2.5 and may differ from the official Air Quality Index, which considers multiple pollutants.
Do not use government logos, emblems or names.

---
## D. User Consent Text
- No consent screen is needed for data collection, because none is collected.
- Notification permission prompt (shown only after user enables alerts): "Allow notifications so NCR Hawa can alert you when tomorrow's air is forecast to be Poor or worse? You can turn this off any time."
- If you ever add location or analytics: add a clear, optional, plain-language consent screen, update this policy, Data Safety form and permissions declaration first.

---
## E. Personal Data Handling Note
MVP: no personal data collected or stored by the developer. Possible exposure points: hosting logs (IP), emails sent to the contact address, tester list (kept outside repo, deleted after the testing period or kept only with consent). Review each release.

---
## F. Data Retention and Deletion Policy
| Data | Where | Retention | Deletion |
|------|-------|-----------|----------|
| On-device settings/cache | user's phone | until user clears/uninstalls | user |
| Hosting logs | provider | [X days] per provider **[VERIFY]** | provider rotation |
| Contact emails | developer mailbox | [X months] | manual |
| Tester list | developer's private store | until test + [X days] | manual |
| Public data archive (not personal) | developer storage | kept for research/evaluation, respecting source licences | on licence change |

**Data Request / Deletion Page** (public URL): "NCR Hawa does not hold personal accounts. To remove app data, clear storage or uninstall. For any other request (for example an email you sent us), write to [EMAIL] and we will respond within [X] days."

---
## G. Third-Party Licence List
Generate from real dependencies (`pip-licenses`; Gradle licence report plugin) and show in the app's "Open source licences".
| Component/data | Version | Licence | Link | Obligation |
|----------------|---------|---------|------|-----------|
| Open-Meteo API data (air quality, weather) | - | CC BY 4.0; free API non-commercial **[VERIFIED]** | open-meteo.com | Attribution to Open-Meteo and CAMS; link "Weather data by Open-Meteo.com" **[VERIFIED]** |
| Copernicus CAMS data (via Open-Meteo) | - | per CAMS terms **[VERIFY]** | ads.atmosphere.copernicus.eu | Cite as Open-Meteo docs require **[VERIFIED]** |
| OpenAQ-aggregated station data | - | per-station licence **[VERIFIED mechanism]** | openaq.org | Per licence |
| NASA FIRMS (if used) | - | **[VERIFY]** | firms.modaps.eosdis.nasa.gov | **[VERIFY]** |
| Python and Android libraries | | | | fill from reports |
Any share-alike, AGPL or non-commercial item needs a decision before release.
