# OpenAQ Observation History Pilot Summary (WP4a)

> **Notice**: This is a 2-week pilot and says nothing about forecast skill.

## 1. Scope & Covered Date Range

- **Covered Period (UTC)**: `2026-11-01T00:30:00Z` to `2026-11-14T23:30:00Z`
- **Covered Period (IST)**: `2026-11-01` to `2026-11-15` (15 calendar days)
- **Target Pollutants**: Hourly $\text{PM}_{2.5}$ and $\text{PM}_{10}$ observations.
- **Pilot Stations**: 5 representative monitors across Delhi-NCR (Central Delhi, Faridabad, Ghaziabad, Gurugram, Noida).

## 2. Completeness and Quality Metrics per Station & Parameter

| Station ID | Area | Provider | Param | Hours Present | Span Expected | Completeness | Longest Gap | Negative | Null | Very High | Flatline | Valid Days (>=18h) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `235` | `ghaziabad` | CPCB | **pm10** | 312 | 336 | 92.9% | 19h | 0 | 0 | 0 | 0 | **N/A** |
| `235` | `ghaziabad` | CPCB | **pm25** | 313 | 336 | 93.2% | 19h | 0 | 0 | 0 | 0 | **12** |
| `301` | `gurugram` | CPCB | **pm10** | 306 | 335 | 91.3% | 19h | 0 | 0 | 0 | 0 | **N/A** |
| `301` | `gurugram` | CPCB | **pm25** | 306 | 335 | 91.3% | 19h | 0 | 0 | 0 | 6 | **12** |
| `5598` | `noida` | CPCB | **pm10** | 279 | 336 | 83.0% | 19h | 0 | 0 | 0 | 0 | **N/A** |
| `5598` | `noida` | CPCB | **pm25** | 290 | 336 | 86.3% | 19h | 0 | 0 | 0 | 0 | **11** |
| `6934` | `faridabad` | CPCB | **pm10** | 314 | 336 | 93.5% | 19h | 0 | 0 | 0 | 0 | **N/A** |
| `6934` | `faridabad` | CPCB | **pm25** | 315 | 336 | 93.8% | 19h | 0 | 0 | 0 | 0 | **12** |
| `8118` | `central_delhi` | AirNow | **pm25** | 309 | 336 | 92.0% | 12h | 0 | 0 | 0 | 0 | **12** |

## 3. Day-by-Day Mean PM2.5 and CPCB Category (IST Calendar Days)

A day is deemed valid if it contains $\ge 18$ valid hourly measurements. Invalid days are marked with `(invalid: <n>h)`.

| Date (IST) | Central Delhi (8118) | Faridabad (6934) | Ghaziabad (235) | Gurugram (301) | Noida (5598) |
|---|---|---|---|---|---|
| `2026-11-01` | 166.7 (very_poor) | 154.1 (very_poor) | 92.1 (poor) | 75.9 (moderate) | 119.6 (poor) |
| `2026-11-02` | 186.9 (very_poor) | 172.4 (very_poor) | 123.1 (very_poor) | 98.7 (poor) | 125.4 (very_poor) |
| `2026-11-03` | 232.6 (very_poor) | *204.5* (very_poor, invalid: 13h) | *131.4* (very_poor, invalid: 13h) | *100.8* (poor, invalid: 13h) | *73.0* (moderate, invalid: 8h) |
| `2026-11-04` | 245.7 (very_poor) | *248.9* (very_poor, invalid: 16h) | *121.4* (very_poor, invalid: 16h) | *116.2* (poor, invalid: 16h) | *175.6* (very_poor, invalid: 16h) |
| `2026-11-05` | 271.2 (severe) | 271.6 (severe) | 180.7 (very_poor) | 129.0 (very_poor) | 117.5 (poor) |
| `2026-11-06` | 264.5 (severe) | 287.2 (severe) | 139.7 (very_poor) | 126.0 (very_poor) | 151.4 (very_poor) |
| `2026-11-07` | 280.8 (severe) | 259.3 (severe) | 159.1 (very_poor) | 132.5 (very_poor) | 133.4 (very_poor) |
| `2026-11-08` | *237.1* (very_poor, invalid: 17h) | 245.8 (very_poor) | 287.4 (severe) | 164.4 (very_poor) | 236.1 (very_poor) |
| `2026-11-09` | *179.1* (very_poor, invalid: 14h) | 230.3 (very_poor) | 168.9 (very_poor) | 131.8 (very_poor) | 149.9 (very_poor) |
| `2026-11-10` | 206.5 (very_poor) | 154.9 (very_poor) | 144.1 (very_poor) | 143.3 (very_poor) | 168.6 (very_poor) |
| `2026-11-11` | 200.0 (very_poor) | 140.5 (very_poor) | 159.7 (very_poor) | 126.8 (very_poor) | 122.3 (very_poor) |
| `2026-11-12` | 317.4 (severe) | 234.4 (very_poor) | 256.5 (severe) | 108.2 (poor) | *322.1* (severe, invalid: 16h) |
| `2026-11-13` | 248.3 (very_poor) | 191.8 (very_poor) | 237.3 (very_poor) | 167.2 (very_poor) | 101.0 (poor) |
| `2026-11-14` | 259.1 (severe) | 189.3 (very_poor) | 232.0 (very_poor) | 154.5 (very_poor) | 131.1 (very_poor) |
| `2026-11-15` | *231.2* (very_poor, invalid: 5h) | *182.8* (very_poor, invalid: 5h) | *225.2* (very_poor, invalid: 5h) | *94.7* (poor, invalid: 5h) | *140.8* (very_poor, invalid: 5h) |

## 4. Key Findings & Empirical Data Characteristics

1. **Zero Disagreements across Fetches**: The two independent downloads (2026-11-26 and 2026-11-27) yielded 100% identical values for identical timestamps across all stations.
2. **Zero Null Records**: The API never emits records with `value: null`. Missing hours are represented as omitted intervals (sparse series).
3. **Flatline Detection**: Station `301` (Gurugram) experienced exactly one 6-hour flatline event at value `112.0 µg/m³` on 2026-11-13. Per QC rules, these hours are included in daily means but flagged in quality audits.
4. **No Extreme Outliers**: Zero readings exceeded the 1000 µg/m³ very-high threshold.
5. **High Data Availability**: Stations achieved 11 to 12 valid days out of 15 calendar days (~80% day coverage). Days with fewer than 18 hours typically occurred at the start/end of the pilot range or during multi-hour network drops (e.g., Nov 3-4 across multiple CPCB stations).
