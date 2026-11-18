# AQ_01. Research and Idea (includes Problem Statement and Scope)

Status: DRAFT v0.1 | 2026-11-15

## 1. Problem statement
Every winter, Delhi-NCR residents plan school runs, exercise, travel and work around bad air. Current apps mostly show *now*. People need a short, understandable look at *tomorrow and the day after*, with an honest sense of how reliable it is.
**[VERIFY with 2-3 cited sources before using any pollution statistic. Do not quote health or death numbers from memory.]**

## 2. Idea
- Collect public pollution and weather data for Delhi-NCR.
- Forecast daily PM2.5 level and the resulting air-quality category for D+1 and D+2.
- Show a simple page/app with category, probability of "Poor or worse", and a short health note.
- Always show how the forecast compares with simple baselines and how it did yesterday.

## 3. Scope
**In:** Delhi-NCR stations (Delhi zones, Noida, Gurugram, Ghaziabad, Faridabad, others you can verify), daily D+1 and D+2, web page first, Android app second, English + Hindi.
**Out (MVP):** hourly minute-by-minute forecasts, indoor air, pollution source attribution, medical advice, accounts, ads, other cities, iOS.

## 4. Honest framing of what the number is
India's AQI is the **worst sub-index across pollutants** **[VERIFIED 2026-11-15: CPCB/IES]**, and CPCB's scheme uses short-term (up to 24-hour) averaging **[VERIFIED]**. A secondary source says at least 3 pollutants including PM2.5 or PM10 are needed for a valid AQI **[VERIFY in CPCB report]**.
Delhi winter AQI is often driven by PM2.5/PM10, but not always. So this app forecasts **PM2.5** and shows a **"PM2.5-based category"**, and says so. Do not label it "official AQI".

CPCB categories **[VERIFIED 2026-11-15]**: Good 0-50, Satisfactory 51-100, Moderate 101-200, Poor 201-300, Very Poor 301-400, Severe 401-500.
PM2.5 breakpoints (24-h, µg/m³) from a published table: Good 0-30, Satisfactory 31-60, Moderate 61-90, Poor 91-120, Very Poor 121-250, Severe 250+. PM10: 0-50, 51-100, 101-250, 251-350, 351-430, 430+. **[VERIFY against the CPCB 2014 National AQI report before coding.]**

## 5. Data source verification (done 2026-11-15)
| Source | Use | What I found | Decision |
|--------|-----|--------------|----------|
| **OpenAQ API v3** | Observed PM2.5/PM10/weather at stations | Needs an API key (X-API-Key header). Data licence varies by original source; the API exposes per-licence flags (commercial use, attribution, redistribution) **[VERIFIED]**. Their FAQ says apps with many users will hit rate limits and browsers are blocked by CORS; use your own backend as a proxy **[VERIFIED]** | **Primary observations source.** Backend only. Check each station's licence before publishing its data. |
| **CPCB / data.gov.in** "Real time Air Quality Index" | Alternative / cross-check | data.gov.in page says live data is shown without human intervention and may contain errors; page also says an API for this resource does not exist and offers "Request API" **[VERIFIED, page may be stale]**. A CEEW write-up (2021) said the CPCB dashboard was often unresponsive, live data is not QA/QC'd, archived data is **[VERIFIED, dated]** | Do not scrape. Use only if an official API/terms exist. **[VERIFY current access and licence.]** |
| **Open-Meteo Air Quality API** (CAMS) | Model forecast: feature + strong baseline | Free for non-commercial use, <10,000 calls/day, CC BY 4.0, attribution to CAMS and Open-Meteo required, commercial use needs a paid plan **[VERIFIED]**. For India the usable data is the **CAMS global forecast: 0.4° (~45 km), 3-hourly, every 12 hours, 5-day forecast, available since Aug 2022 [VERIFIED]**. The 11 km European forecast does not cover India. | Use for forecast features and as baseline B2. Keep app **non-commercial: no ads, no paid features**. **[VERIFY]** it counts as non-commercial for a free Play app by an individual; if unsure, contact them. |
| **Open-Meteo weather API** | Weather forecast + history features | Same free non-commercial terms and attribution link requirement **[VERIFIED]** | Use. Show "Weather data by Open-Meteo.com" with link. |
| **NASA FIRMS** | Optional: fire hotspots (stubble burning) | Free MAP_KEY by email; rate limit reported as 5,000 transactions / 10 min per key (secondary source) **[VERIFIED, secondary]** | Optional feature (COULD tier). |
| Scraping CPCB / IQAir / AQI.in / other apps | - | Terms unknown, fragile | **Do not use.** |

**Key risk found:** coarse 45 km CAMS grid is a weak local baseline for city-level pollution, which is exactly why a locally trained model may add value, and why it may not.

## 6. Existing solutions (you must fill in)
Task: list 5 apps/sites (government apps, commercial AQI apps, research forecasts). For each: does it forecast, how far ahead, does it show accuracy, link. Do NOT claim "no one forecasts". Claim only: **local, transparent, baseline-compared, no-ads, Hindi/English.**
| App | Forecast? | Horizon | Shows accuracy? | Notes |
|-----|-----------|---------|-----------------|-------|

## 7. Why this idea works
- Daily ground truth lets you verify every forecast.
- Data is public and recurring; evaluation is objective.
- No personal data needed.

## 8. Why it might fail
- Persistence ("tomorrow = today") is hard to beat for 24h; the model may add little. That is a result, not a failure, if reported honestly.
- Station data has gaps and errors.
- Competing apps already exist.
- Winter is short; the app may miss most of this winter if the Play process drags (see AQ_04).

## 9. User interviews (fill in, minimum 3)
- Parent planning school run: ____
- Regular outdoor exerciser: ____
- Person with asthma/heart condition or their family: ____ (ask what they actually do with the information; do not give medical advice)
Questions: What do you check today? What decision does it change? What would make you trust a forecast?

## 10. Decision
Go if: (a) OpenAQ licences for enough Delhi-NCR stations permit your use, (b) a baseline evaluation can be produced in 2 weeks, (c) you have 3 interviews. Otherwise rescope.
