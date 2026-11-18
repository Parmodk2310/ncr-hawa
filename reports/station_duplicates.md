# Station Duplicate Detection Report (Task A-003b)

## Overview
- **Input Licences File**: `data/licences.csv`
- **Distance Threshold (`--dup-m`)**: `500.0 m` (maintainer guess)
- **Total Locations Evaluated**: `144`
- **Likely Duplicate Groups Found**: `13`
- **Total Duplicate Stations**: `27`
- **Same-Name Stations Separated Beyond Threshold**: `24`

## 1. Likely Duplicate Groups (Distance <= 500 m, Same Normalised Name)

### Group `DUP-01`: r k puram, delhi - dpcc
- **Stations in Group**: `2`
- **Maximum Distance Apart**: `0.0 m`

| Station ID | Provider | Distance Apart | datetime_first | datetime_last | Licence Name | has_pm25 |
|---|---|---|---|---|---|---|
| 17 | `CPCB` | 0.0 m (to 7044) | `2016-02-05T14:55:00Z` | `2026-11-18T18:00:00Z` | `unknown` | `True` |
| 7044 | `caaqm` | 0.0 m (to 17) | `2018-08-10T06:00:00Z` | `2022-10-31T00:45:00Z` | `unknown` | `True` |

### Group `DUP-02`: punjabi bagh, delhi - dpcc
- **Stations in Group**: `2`
- **Maximum Distance Apart**: `0.0 m`

| Station ID | Provider | Distance Apart | datetime_first | datetime_last | Licence Name | has_pm25 |
|---|---|---|---|---|---|---|
| 50 | `CPCB` | 0.0 m (to 6357) | `2016-02-05T14:55:00Z` | `2026-11-18T18:00:00Z` | `unknown` | `True` |
| 6357 | `caaqm` | 0.0 m (to 50) | `2018-08-10T06:00:00Z` | `2022-10-16T14:15:00Z` | `unknown` | `True` |

### Group `DUP-03`: md university, rohtak - hspcb
- **Stations in Group**: `2`
- **Maximum Distance Apart**: `249.6 m`

| Station ID | Provider | Distance Apart | datetime_first | datetime_last | Licence Name | has_pm25 |
|---|---|---|---|---|---|---|
| 346 | `CPCB` | 249.6 m (to 7283) | `2016-03-22T00:30:00Z` | `2018-02-22T03:45:00Z` | `unknown` | `True` |
| 7283 | `CPCB` | 249.6 m (to 346) | `2020-01-01T11:45:00Z` | `2026-11-18T18:00:00Z` | `unknown` | `True` |

### Group `DUP-04`: anand vihar, delhi - dpcc
- **Stations in Group**: `2`
- **Maximum Distance Apart**: `90.2 m`

| Station ID | Provider | Distance Apart | datetime_first | datetime_last | Licence Name | has_pm25 |
|---|---|---|---|---|---|---|
| 5509 | `caaqm` | 90.2 m (to 10487) | `2018-03-09T03:30:00Z` | `2022-10-31T00:30:00Z` | `unknown` | `True` |
| 10487 | `caaqm` | 90.2 m (to 5509) | `2018-08-13T11:00:00Z` | `2021-09-20T07:45:00Z` | `unknown` | `True` |

### Group `DUP-05`: mandir marg, new delhi - dpcc
- **Stations in Group**: `2`
- **Maximum Distance Apart**: `105.7 m`

| Station ID | Provider | Distance Apart | datetime_first | datetime_last | Licence Name | has_pm25 |
|---|---|---|---|---|---|---|
| 5641 | `caaqm` | 105.7 m (to 6358) | `2018-03-09T03:30:00Z` | `2018-05-12T04:30:00Z` | `unknown` | `True` |
| 6358 | `CPCB` | 105.7 m (to 5641) | `2018-08-10T06:00:00Z` | `2026-11-18T18:00:00Z` | `unknown` | `True` |

### Group `DUP-06`: dr. karni singh shooting range, delhi - dpcc
- **Stations in Group**: `2`
- **Maximum Distance Apart**: `129.2 m`

| Station ID | Provider | Distance Apart | datetime_first | datetime_last | Licence Name | has_pm25 |
|---|---|---|---|---|---|---|
| 5744 | `caaqm` | 129.2 m (to 6934) | `2018-04-16T07:30:00Z` | `2018-05-12T04:45:00Z` | `unknown` | `True` |
| 6934 | `CPCB` | 129.2 m (to 5744) | `2018-08-10T06:30:00Z` | `2026-11-18T18:00:00Z` | `unknown` | `True` |

### Group `DUP-07`: vivek vihar, delhi - dpcc
- **Stations in Group**: `2`
- **Maximum Distance Apart**: `448.7 m`

| Station ID | Provider | Distance Apart | datetime_first | datetime_last | Licence Name | has_pm25 |
|---|---|---|---|---|---|---|
| 5753 | `caaqm` | 448.7 m (to 6938) | `2018-04-16T06:00:00Z` | `2018-05-12T06:00:00Z` | `unknown` | `True` |
| 6938 | `CPCB` | 448.7 m (to 5753) | `2018-12-15T15:15:00Z` | `2026-11-18T18:00:00Z` | `unknown` | `True` |

### Group `DUP-08`: jawaharlal nehru stadium, delhi - dpcc
- **Stations in Group**: `2`
- **Maximum Distance Apart**: `328.1 m`

| Station ID | Provider | Distance Apart | datetime_first | datetime_last | Licence Name | has_pm25 |
|---|---|---|---|---|---|---|
| 5754 | `caaqm` | 328.1 m (to 6957) | `2018-04-16T14:30:00Z` | `2018-05-12T06:30:00Z` | `unknown` | `True` |
| 6957 | `CPCB` | 328.1 m (to 5754) | `2018-08-10T06:00:00Z` | `2026-11-18T18:00:00Z` | `unknown` | `True` |

### Group `DUP-09`: major dhyan chand national stadium, delhi - dpcc
- **Stations in Group**: `2`
- **Maximum Distance Apart**: `282.6 m`

| Station ID | Provider | Distance Apart | datetime_first | datetime_last | Licence Name | has_pm25 |
|---|---|---|---|---|---|---|
| 5755 | `caaqm` | 282.6 m (to 6929) | `2018-04-26T23:00:00Z` | `2018-05-12T04:30:00Z` | `unknown` | `True` |
| 6929 | `CPCB` | 282.6 m (to 5755) | `2018-08-10T07:00:00Z` | `2026-11-18T18:00:00Z` | `unknown` | `True` |

### Group `DUP-10`: ashok vihar, delhi - dpcc
- **Stations in Group**: `2`
- **Maximum Distance Apart**: `52.2 m`

| Station ID | Provider | Distance Apart | datetime_first | datetime_last | Licence Name | has_pm25 |
|---|---|---|---|---|---|---|
| 5762 | `caaqm` | 52.2 m (to 8917) | `2018-04-16T15:00:00Z` | `2018-05-12T06:00:00Z` | `unknown` | `True` |
| 8917 | `CPCB` | 52.2 m (to 5762) | `2018-12-15T15:00:00Z` | `2026-11-18T18:00:00Z` | `unknown` | `True` |

### Group `DUP-11`: murthal, sonipat - hspcb
- **Stations in Group**: `2`
- **Maximum Distance Apart**: `0.0 m`

| Station ID | Provider | Distance Apart | datetime_first | datetime_last | Licence Name | has_pm25 |
|---|---|---|---|---|---|---|
| 6951 | `CPCB` | 0.0 m (to 10906) | `2019-02-13T00:15:00Z` | `2026-11-18T18:00:00Z` | `unknown` | `True` |
| 10906 | `caaqm` | 0.0 m (to 6951) | `2020-01-02T08:00:00Z` | `2022-10-16T16:00:00Z` | `unknown` | `True` |

### Group `DUP-12`: shyam nagar, palwal - hspcb
- **Stations in Group**: `2`
- **Maximum Distance Apart**: `0.0 m`

| Station ID | Provider | Distance Apart | datetime_first | datetime_last | Licence Name | has_pm25 |
|---|---|---|---|---|---|---|
| 7280 | `CPCB` | 0.0 m (to 7281) | `2019-02-13T00:15:00Z` | `2026-11-18T18:00:00Z` | `unknown` | `True` |
| 7281 | `caaqm` | 0.0 m (to 7280) | `2020-01-01T10:15:00Z` | `2022-10-31T01:30:00Z` | `unknown` | `True` |

### Group `DUP-13`: a-block sector 51 noida
- **Stations in Group**: `3`
- **Maximum Distance Apart**: `225.2 m`

| Station ID | Provider | Distance Apart | datetime_first | datetime_last | Licence Name | has_pm25 |
|---|---|---|---|---|---|---|
| 6551848 | `AirGradient` | 128.4 m (to 6551894); 225.2 m (to 6552066) | `2026-10-29T12:00:00Z` | `2026-11-18T01:00:00Z` | `CC BY 4.0` | `True` |
| 6551894 | `AirGradient` | 128.4 m (to 6551848); 219.1 m (to 6552066) | `unknown` | `unknown` | `CC BY 4.0` | `True` |
| 6552066 | `AirGradient` | 225.2 m (to 6551848); 219.1 m (to 6551894) | `unknown` | `unknown` | `CC BY 4.0` | `True` |

## 2. Same Name, Far Apart (> 500 m)

These stations share identical normalised names but are located farther apart than `500.0 m`. Per project rules, they are **not** treated as duplicates.

| Station ID | Normalised Name | Provider | Closest Counterpart | Distance Apart | datetime_last |
|---|---|---|---|---|---|
| 5540 | `punjabi bagh, delhi - dpcc` | `caaqm` | Station 50 | **778.8 m** | `2018-05-13T11:30:00Z` |
| 5552 | `md university, rohtak - hspcb` | `caaqm` | Station 346 | **668.7 m** | `2020-01-01T11:00:00Z` |
| 2503 | `shadipur, delhi - cpcb` | `CPCB` | Station 5630 | **1.05 km** | `2018-02-22T02:45:00Z` |
| 5630 | `shadipur, delhi - cpcb` | `CPCB` | Station 2503 | **1.05 km** | `2026-11-18T18:00:00Z` |
| 5742 | `patparganj, delhi - dpcc` | `caaqm` | Station 6960 | **850.1 m** | `2018-05-13T11:30:00Z` |
| 6960 | `patparganj, delhi - dpcc` | `CPCB` | Station 5742 | **850.1 m** | `2026-11-18T18:00:00Z` |
| 5743 | `rohini, delhi - dpcc` | `caaqm` | Station 10831 | **6.13 km** | `2018-05-12T06:30:00Z` |
| 10831 | `rohini, delhi - dpcc` | `CPCB` | Station 5743 | **6.13 km** | `2026-11-18T18:00:00Z` |
| 5759 | `sonia vihar, delhi - dpcc` | `caaqm` | Station 8475 | **6.01 km** | `2018-05-12T05:00:00Z` |
| 8475 | `sonia vihar, delhi - dpcc` | `CPCB` | Station 5759 | **6.01 km** | `2026-11-18T18:00:00Z` |
| 5760 | `dwarka-sector 8, delhi - dpcc` | `caaqm` | Station 6931 | **26.91 km** | `2018-05-12T05:00:00Z` |
| 6931 | `dwarka-sector 8, delhi - dpcc` | `CPCB` | Station 5760 | **26.91 km** | `2026-11-18T18:00:00Z` |
| 5761 | `jahangirpuri, delhi - dpcc` | `caaqm` | Station 8235 | **1.25 km** | `2018-05-12T06:30:00Z` |
| 8235 | `jahangirpuri, delhi - dpcc` | `CPCB` | Station 5761 | **1.25 km** | `2026-11-18T18:00:00Z` |
| 5763 | `narela, delhi - dpcc` | `caaqm` | Station 10485 | **7.12 km** | `2018-05-12T06:00:00Z` |
| 10485 | `narela, delhi - dpcc` | `CPCB` | Station 5763 | **7.12 km** | `2026-11-18T18:00:00Z` |
| 5765 | `okhla phase-2, delhi - dpcc` | `caaqm` | Station 8239 | **802.2 m** | `2018-05-13T10:00:00Z` |
| 8239 | `okhla phase-2, delhi - dpcc` | `CPCB` | Station 5765 | **802.2 m** | `2026-11-18T18:00:00Z` |
| 5766 | `nehru nagar, delhi - dpcc` | `caaqm` | Station 8365 | **918.7 m** | `2018-05-13T10:00:00Z` |
| 8365 | `nehru nagar, delhi - dpcc` | `CPCB` | Station 5766 | **918.7 m** | `2026-11-18T18:00:00Z` |
| 6314 | `nise gwal pahari, gurugram - imd` | `caaqm` | Station 10921 | **29.26 km** | `2018-11-16T04:00:00Z` |
| 10921 | `nise gwal pahari, gurugram - imd` | `CPCB` | Station 6314 | **29.26 km** | `2026-11-18T18:00:00Z` |
| 7434 | `east arjun nagar, delhi - cpcb` | `caaqm` | Station 8092 | **876.3 m** | `2020-02-10T03:00:00Z` |
| 8092 | `east arjun nagar, delhi - cpcb` | `caaqm` | Station 7434 | **876.3 m** | `2022-01-26T07:00:00Z` |

## 3. Decision Guidance for Candidates CSV
1. In candidates CSV, duplicates are tagged with `duplicate_group_id` and `dup_note`.
2. When deciding which station to keep in each duplicate group:
   - Prefer stations with active reporting (`datetime_last` in 2026).
   - Prefer reference-grade monitors (`is_monitor = True`).
   - Mark one as `use` and duplicates as `exclude` in `decision`.
3. The `decision` column remains empty for maintainer review.
