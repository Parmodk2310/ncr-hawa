# Station & Licence Shortlist Summary (Task A-003)

## Overview
- **Input Licences File**: `data/licences.csv`
- **Input Areas File**: `configs/areas.json`
- **Reference UTC Date**: `2026-11-18`
- **Distance Threshold (`--max-km`)**: `25.0 km` (maintainer guess)
- **Duplicate Threshold (`--dup-m`)**: `500.0 m` (maintainer guess)
- **Total Locations Evaluated**: `144`
- **Candidate Locations Kept**: `119`
- **Locations Outside Threshold**: `25`
- **Duplicate Groups Detected**: `13`

## 1. Station Distribution by Forecast Area
| Area ID | Description / Center | Radius Limit | Station Count | Share |
|---|---|---|---|---|
| `central_delhi` | Central Delhi | <= 25.0 km | 68 | 47.2% |
| `noida` | Noida | <= 25.0 km | 12 | 8.3% |
| `gurugram` | Gurugram | <= 25.0 km | 15 | 10.4% |
| `ghaziabad` | Ghaziabad | <= 25.0 km | 16 | 11.1% |
| `faridabad` | Faridabad | <= 25.0 km | 8 | 5.6% |
| `outside` | Beyond 25.0 km radius | > 25.0 km | 25 | 17.4% |
| **Total** | All Locations | - | 144 | 100.0% |

## 2. Provider Breakdown
| Provider | Total Count | Kept Candidates | Licence Status |
|---|---|---|---|
| `CPCB` | 83 | 66 | - |
| `caaqm` | 30 | 25 | - |
| `N/A` | 16 | 13 | - |
| `AirGradient` | 12 | 12 | - |
| `StateAir NewDelhi` | 1 | 1 | - |
| `AirNow` | 1 | 1 | - |
| `Clarity` | 1 | 1 | - |

## 3. Licence Status
- **Listed Licence**: 14
  - `CC BY 4.0`: 12
  - `US Public Domain`: 1
  - `CC0 1.0`: 1
- **No Licence**: 130

> [!IMPORTANT]
> Per data policy (`AQ_11`), missing licence data is reported as `unknown`.
> If redistribution is unconfirmed, only derived forecasts may be published, never raw station observations.

## 4. Sensor & Parameter Characteristics
| Parameter | Value | Count | Share |
|---|---|---|---|
| `has_pm25` | `yes` | 142 | 98.6% |
| `has_pm25` | `no` | 2 | 1.4% |
| `has_pm25` | `unknown` | 0 | 0.0% |
| `is_mobile` | `yes` | 0 | 0.0% |
| `is_mobile` | `no` | 144 | 100.0% |
| `is_mobile` | `unknown` | 0 | 0.0% |
| `is_monitor` | `yes` | 115 | 79.9% |
| `is_monitor` | `no` | 29 | 20.1% |
| `is_monitor` | `unknown` | 0 | 0.0% |

## 5. Data Recency (`datetime_last`)
- **Reference Date**: `2026-11-18` (UTC)
- **Active within last 30 days** (>= `2026-10-19`): **100**
- **Historical only** (> 30 days old): **40**
- **Unknown / Missing date**: **4**

## 6. Duplicate Station Summary
- **Duplicate Distance Threshold (`--dup-m`)**: `500.0 m`
- **Likely Duplicate Groups**: `13`
- **Same-Name Far Apart**: `24`
- Detailed audit available in `reports/station_duplicates.md`.

## 7. Outside Locations (> 25 km threshold)
Total outside locations: **25**
| Station ID | Name | Provider | Lat | Lon | Nearest Distance (km) |
|---|---|---|---|---|---|
| 6936 | Arya Nagar, Bahadurgarh - HSPCB | CPCB | 28.6701 | 76.9254 | 25.50 |
| 10485 | Narela, Delhi - DPCC | CPCB | 28.822836 | 77.101981 | 25.90 |
| 7280 | Shyam Nagar, Palwal - HSPCB | CPCB | 28.1485564 | 77.3320667 | 29.15 |
| 7281 | Shyam Nagar, Palwal - HSPCB | caaqm | 28.1485564 | 77.3320667 | 29.15 |
| 5763 | Narela, Delhi - DPCC | caaqm | 28.8446874 | 77.0332666 | 31.27 |
| 8319 | Anand Vihar, Hapur - UPPCB | CPCB | 28.725645 | 77.749675 | 32.75 |
| 5588 | RIICO Ind. Area III, Bhiwadi - RSPCB | CPCB | 28.194909 | 76.862296 | 33.74 |
| 3409519 | Vasundhara Nagar_UIT, Bhiwadi - RSPCB | CPCB | 28.207266 | 76.829265 | 34.29 |
| 301388 | Sardar Patel Inter College, Baghpat - UPPCB | CPCB | 28.964949 | 77.278761 | 35.57 |
| 6949 | Municipal Corporation Office, Dharuhera -  HSPCB | CPCB | 28.2068 | 76.7997 | 36.07 |
| 6979 | New Collectorate, Baghpat - UPPCB | caaqm | 28.974801000000003 | 77.21335699999999 | 39.42 |
| 6311325 | MIET College, Meerut - UPPCB | N/A | 28.972677 | 77.641018 | 39.95 |
| 6976 | Jai Bhim Nagar, Meerut - UPPCB | CPCB | 28.9535882 | 77.7622941 | 45.90 |
| 6985 | Yamunapuram, Bulandshahr - UPPCB | CPCB | 28.406963 | 77.849831 | 47.32 |
| 6951 | Murthal, Sonipat - HSPCB | CPCB | 29.0272 | 77.0621 | 48.58 |
| 10906 | Murthal, Sonipat - HSPCB | caaqm | 29.027199999999997 | 77.0621 | 48.58 |
| 7833 | Ganga Nagar, Meerut - UPPCB | CPCB | 28.999264 | 77.7590354 | 49.31 |
| 6487074 | Nagar Palika Parishad, Baraut - UPPCB | N/A | 29.09956 | 77.26235 | 50.17 |
| 7720 | Pallavpuram Phase 2, Meerut - UPPCB | CPCB | 29.06351 | 77.709723 | 52.06 |
| 346439 | Kalindi Kunj, Khurja - UPPCB | CPCB | 28.234892699999996 | 77.8683002 | 57.79 |
| 5552 | MD University, Rohtak - HSPCB | caaqm | 28.870083 | 76.6205 | 60.63 |
| 346 | MD University, Rohtak - HSPCB | CPCB | 28.876028 | 76.619464 | 61.19 |
| 7283 | MD University, Rohtak - HSPCB | CPCB | 28.87793 | 76.620825 | 61.26 |
| 6947 | General Hospital, Mandikhera - HSPCB | CPCB | 27.9002 | 76.9938 | 62.35 |
| 6404322 | New Anaj Mandi, Khairthal - RSPCB | N/A | 27.8015617 | 76.6365217 | 82.76 |

## 8. Next Steps & Decision Guide
1. Inspect `data/stations_candidates.csv`.
2. Check duplicate tags (`duplicate_group_id`, `dup_note`).
3. Fill `decision` column (`use`, `publish`, `exclude`) per `AQ_11`.
4. Do not invent licences; unverified flags stay `unknown`.
