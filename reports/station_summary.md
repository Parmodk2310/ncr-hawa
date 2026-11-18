# Station & Licence Shortlist Summary (Task A-003)

## Overview
- **Input Licences File**: `C:\Users\HP\AppData\Local\Temp\pytest-of-HP\pytest-5\test_analyse_stations_include_0\licences.csv`
- **Input Areas File**: `C:\Users\HP\AppData\Local\Temp\pytest-of-HP\pytest-5\test_analyse_stations_include_0\areas.json`
- **Reference UTC Date**: `2026-11-18`
- **Distance Threshold (`--max-km`)**: `25.0 km` (maintainer guess)
- **Total Locations Evaluated**: `2`
- **Candidate Locations Kept**: `2` (`stations_candidates.csv`)
- **Locations Outside Threshold**: `1`

## 1. Station Distribution by Forecast Area
| Area ID | Description / Center | Radius Limit | Station Count | Share |
|---|---|---|---|---|
| `central_delhi` | Central Delhi | <= 25.0 km | 1 | 50.0% |
| `noida` | Noida | <= 25.0 km | 0 | 0.0% |
| `outside` | Beyond 25.0 km radius | > 25.0 km | 1 | 50.0% |
| **Total** | All Locations | - | **2** | **100.0%** |

## 2. Provider Breakdown
| Provider | Total Count | Kept Candidates | Licence Status |
|---|---|---|---|
| `CPCB` | 2 | 2 | - |

## 3. Licence Status
- **Listed Licence**: 0
- **No Licence / Unknown**: 2

> [!IMPORTANT]
> Per project data policy (`AQ_11`), missing licence data is reported as `unknown` / `no licence`.
> If redistribution is not confirmed, only derived model forecasts may be published, never raw station observations.

## 4. Sensor & Parameter Characteristics
| Parameter | Value | Count | Share |
|---|---|---|---|
| `has_pm25` | `yes` | 0 | 0.0% |
| `has_pm25` | `no` | 0 | 0.0% |
| `has_pm25` | `unknown` | 2 | 100.0% |
| `is_mobile` | `yes` | 0 | 0.0% |
| `is_mobile` | `no` | 0 | 0.0% |
| `is_mobile` | `unknown` | 2 | 100.0% |
| `is_monitor` | `yes` | 0 | 0.0% |
| `is_monitor` | `no` | 0 | 0.0% |
| `is_monitor` | `unknown` | 2 | 100.0% |

## 5. Data Recency (`datetime_last`)
- **Reference Date**: `2026-11-18` (UTC)
- **Active within last 30 days** (>= `2026-10-19`): **0**
- **Historical only** (> 30 days old): **0**
- **Unknown / Missing date**: **2**

## 6. Outside Locations (> 25 km threshold)
Total outside locations: **1**
| Station ID | Name | Provider | Lat | Lon | Nearest Distance (km) |
|---|---|---|---|---|---|
| 2 | Station Out | CPCB | 28.876 | 76.619 | 64.77 |

## 7. Next Steps & Decision Guide
1. Inspect `data/stations_candidates.csv`.
2. Fill `decision` column (`use`, `publish`, or `exclude`) per `AQ_11`.
3. Do not invent licences; unverified flags stay `unknown`.
