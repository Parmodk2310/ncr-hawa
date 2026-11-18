# AQ_05. Design Document

Status: DRAFT v0.1

## 1. Principles
- Answer one question first: **"How will the air be tomorrow?"**
- Plain words, Hindi + English, large text, high contrast.
- Never hide uncertainty. Always show data time and source.
- Colour is not the only signal: always show the category name.
- No scary or alarmist language; no medical claims.

## 2. Screens (app) / sections (web)
1. **Home**
   - Area picker (top). Last updated time (IST).
   - Card "Now": PM2.5 value, category (PM2.5-based), data age.
   - Card "Tomorrow" and "Day after": category, PM2.5 range, "chance of Poor or worse: x%" (if calibrated).
   - Line: "Simple guess (same as today): <category>" so users see the baseline.
   - Health note for the forecast category (short).
2. **Forecast detail**
   - Interval bar for each day; how this model did over the last 7 days (hit/miss vs baseline).
3. **About and data**
   - Data sources with licences/attribution, forecast method in 5 lines, accuracy summary page, disclaimer, privacy policy link, contact.
4. **Settings**
   - Language, area, notification on/off and threshold (Poor or worse), data refresh info.
5. **First run**
   - Disclaimer: independent app, not official, not medical advice. Pick area. Notification permission asked only when user turns alerts on.

## 3. Category colours and labels (follow CPCB names)
Good, Satisfactory, Moderate, Poor, Very Poor, Severe, using a colour scale with sufficient contrast. Label as "PM2.5-based category".

## 4. Health note (draft, to be reviewed; see AQ_16)
General, cautious, tied to category. Example structure: one line for everyone, one line for sensitive groups (children, older adults, people with lung or heart conditions), one practical tip (limit long outdoor exertion; keep windows closed at peak hours; consider a well-fitting mask). Add: "This is general information, not medical advice. If you feel unwell, speak to a doctor." Base wording on CPCB's published health statements and cite them **[VERIFY text before use]**.

## 5. States to design
No internet; stale data (>X hours); no data for area; forecast unavailable (show baseline only, labelled); source outage; first run; notification denied; language switch; low storage.

## 6. Empty/missing data rule
Missing is never shown as "Good". Show "No data" in grey with reason.

## 7. Performance
- JSON under ~100 KB per area per refresh (set budget); gzip.
- Cache last response; refresh at most every few hours; respect battery.
- Test on a low-memory phone and slow network.

## 8. Accessibility
48dp targets, scalable text, TalkBack labels, category text with every colour.

## 9. Assets
Own icon and graphics. No government emblems. No copied map tiles or logos.

## 10. Web page
Single static page, same content hierarchy, shareable URL, mobile-first, includes "Weather data by Open-Meteo.com" link and CAMS attribution **[VERIFIED requirement]**.
