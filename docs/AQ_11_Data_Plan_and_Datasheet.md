# AQ_11. Data Plan, Datasheet, Source and Licence Record

Status: TEMPLATES + verified findings. Fill every blank from real data.

## A. Source and Licence Record
| Source | Endpoint | Auth | Licence/terms | Attribution | Redistribution | Commercial | Checked on |
|--------|----------|------|---------------|-------------|----------------|-----------|------------|
| OpenAQ v3 (station obs) | api.openaq.org/v3 | API key (X-API-Key) | Varies per station source; read via the licences resource **[VERIFIED mechanism]** | per licence | per licence | per licence | 2026-11-15 (mechanism) |
| Open-Meteo Air Quality (CAMS global) | air-quality-api.open-meteo.com/v1/air-quality | none (free) | Free for non-commercial use, CC BY 4.0, <10,000 calls/day **[VERIFIED]** | Required: CAMS ENSEMBLE/global provider + Open-Meteo **[VERIFIED]** | CC BY 4.0 allows sharing with attribution | Needs paid subscription | 2026-11-15 |
| Open-Meteo Weather | api.open-meteo.com/v1/forecast | none | Same free non-commercial terms; link "Weather data by Open-Meteo.com" **[VERIFIED]** | Required | CC BY 4.0 | Paid | 2026-11-15 |
| NASA FIRMS (optional) | firms.modaps.eosdis.nasa.gov/api | free MAP_KEY (email) | **[VERIFY terms and citation]** | **[VERIFY]** | **[VERIFY]** | **[VERIFY]** | |
| CPCB / data.gov.in | - | - | **[VERIFY]** access and licence | - | - | - | |

Per-station licence table: `data/licences.csv` columns: station_id, name, provider, licence_name, commercialUseAllowed, attributionRequired, redistributionAllowed, source_url, checked_on, decision (use/publish/exclude).
Rule: if redistribution is not allowed for a station, publish only your **derived forecast**, not that station's raw readings, and do not list it by raw values.

## B. Datasheet (fill after audit)
1. **Motivation:** support a Delhi-NCR daily PM2.5 forecast, verified against station data.
2. **Composition:** stations ____; hourly rows ____; date range ____; pollutants available ____; missing share per station ____.
3. **Collection:** OpenAQ aggregates government and other sources; frequency 10 min to 24 h **[VERIFIED]**; only stationary ground-level data **[VERIFIED]**. Sensor types per station ____ (reference-grade vs low-cost) ____.
4. **Quality:** CPCB live data is not QA/QC'd in the same way as archives (2021 report) **[VERIFIED, dated]**; document what you see: spikes, flatlines, negatives, duplicate stamps.
5. **Preprocessing:** timezone to UTC; dedupe; range checks; daily aggregation rule; completeness threshold ____ (document).
6. **Splits:** train / validation / frozen test seasons ____; leakage controls (AQ_03).
7. **Known limitations:** station coverage uneven; CAMS grid 0.4° (~45 km); events (Diwali, burning) are hard; sensor changes over time; data revisions.
8. **Maintenance:** archive runs forever; schema changes detected by validation; yearly licence re-check.

## C. Data Quality and "Labelling" Rules (target = observed daily PM2.5)
- A day's target is valid only if completeness rule is met (set: ____ of 24 hourly values).
- Remove physically impossible values (negative, absurdly high) using a documented threshold; log how many removed.
- Flag flatline sensors (identical values for N hours; set N).
- Spike handling: do not delete high values just because they are high (real severe events exist). Remove only if a rule shows instrument error, and log it.
- Station comparability: do not mix low-cost and reference sensors without noting it; evaluate separately if possible.
- Keep a data-issues log: date, station, issue, action.

## D. Archive plan (start now)
Daily snapshots of: observations, CAMS forecast issuances, weather forecast issuances, (optional) FIRMS. These become your own honest training/evaluation set that avoids hindsight leakage. Store raw + date; back up.

## E. Third-party data notices
Keep `DATA_NOTICES.md` with required attributions and links; show them in the app About screen.
