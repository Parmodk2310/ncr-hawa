# Station Duplicate Detection Report (1000 m Threshold)

## Overview
- **Input Licences File**: `data/licences.csv`
- **Distance Threshold (`--dup-m`)**: `1000 m` (maintainer guess)
- **Total Locations Evaluated**: `144`
- **Likely Duplicate Groups Found**: `17`
- **Total Duplicate Stations**: `37`
- **Same-Name Stations Separated Beyond Threshold**: `14`

## 1. Likely Duplicate Groups (<= 1000 m, Same Name)

### Group `DUP-01`: r k puram, delhi - dpcc
- **Stations in Group**: `2`
- **Maximum Distance Apart**: `0.0 m`

| Station ID | Provider | Distance Apart | datetime_first | datetime_last | Licence Name | has_pm25 |
|---|---|---|---|---|---|---|
| 17 | `CPCB` | 0.0 m (to 7044) | `2016-02-05T14:55:00Z` | `2026-11-18T18:00:00Z` | `unknown` | `True` |
| 7044 | `caaqm` | 0.0 m (to 17) | `2018-08-10T06:00:00Z` | `2022-10-31T00:45:00Z` | `unknown` | `True` |

### Group `DUP-02`: punjabi bagh, delhi - dpcc
- **Stations in Group**: `3`
- **Maximum Distance Apart**: `778.8 m`

| Station ID | Provider | Distance Apart | datetime_first | datetime_last | Licence Name | has_pm25 |
|---|---|---|---|---|---|---|
| 50 | `CPCB` | 778.8 m (to 5540); 0.0 m (to 6357) | `2016-02-05T14:55:00Z` | `2026-11-18T18:00:00Z` | `unknown` | `True` |
| 5540 | `caaqm` | 778.8 m (to 50); 778.8 m (to 6357) | `2018-03-09T03:30:00Z` | `2018-05-13T11:30:00Z` | `unknown` | `True` |
| 6357 | `caaqm` | 0.0 m (to 50); 778.8 m (to 5540) | `2018-08-10T06:00:00Z` | `2022-10-16T14:15:00Z` | `unknown` | `True` |

### Group `DUP-03`: md university, rohtak - hspcb
- **Stations in Group**: `3`
- **Maximum Distance Apart**: `873.1 m`

| Station ID | Provider | Distance Apart | datetime_first | datetime_last | Licence Name | has_pm25 |
|---|---|---|---|---|---|---|
| 346 | `CPCB` | 668.7 m (to 5552); 249.6 m (to 7283) | `2016-03-22T00:30:00Z` | `2018-02-22T03:45:00Z` | `unknown` | `True` |
| 5552 | `caaqm` | 668.7 m (to 346); 873.1 m (to 7283) | `2018-03-09T06:00:00Z` | `2020-01-01T11:00:00Z` | `unknown` | `True` |
| 7283 | `CPCB` | 249.6 m (to 346); 873.1 m (to 5552) | `2020-01-01T11:45:00Z` | `2026-11-18T18:00:00Z` | `unknown` | `True` |

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

### Group `DUP-06`: patparganj, delhi - dpcc
- **Stations in Group**: `2`
- **Maximum Distance Apart**: `850.1 m`

| Station ID | Provider | Distance Apart | datetime_first | datetime_last | Licence Name | has_pm25 |
|---|---|---|---|---|---|---|
| 5742 | `caaqm` | 850.1 m (to 6960) | `2018-04-16T07:30:00Z` | `2018-05-13T11:30:00Z` | `unknown` | `True` |
| 6960 | `CPCB` | 850.1 m (to 5742) | `2018-08-10T06:00:00Z` | `2026-11-18T18:00:00Z` | `unknown` | `True` |

### Group `DUP-07`: dr. karni singh shooting range, delhi - dpcc
- **Stations in Group**: `2`
- **Maximum Distance Apart**: `129.2 m`

| Station ID | Provider | Distance Apart | datetime_first | datetime_last | Licence Name | has_pm25 |
|---|---|---|---|---|---|---|
| 5744 | `caaqm` | 129.2 m (to 6934) | `2018-04-16T07:30:00Z` | `2018-05-12T04:45:00Z` | `unknown` | `True` |
| 6934 | `CPCB` | 129.2 m (to 5744) | `2018-08-10T06:30:00Z` | `2026-11-18T18:00:00Z` | `unknown` | `True` |

### Group `DUP-08`: vivek vihar, delhi - dpcc
- **Stations in Group**: `2`
- **Maximum Distance Apart**: `448.7 m`

| Station ID | Provider | Distance Apart | datetime_first | datetime_last | Licence Name | has_pm25 |
|---|---|---|---|---|---|---|
| 5753 | `caaqm` | 448.7 m (to 6938) | `2018-04-16T06:00:00Z` | `2018-05-12T06:00:00Z` | `unknown` | `True` |
| 6938 | `CPCB` | 448.7 m (to 5753) | `2018-12-15T15:15:00Z` | `2026-11-18T18:00:00Z` | `unknown` | `True` |

### Group `DUP-09`: jawaharlal nehru stadium, delhi - dpcc
- **Stations in Group**: `2`
- **Maximum Distance Apart**: `328.1 m`

| Station ID | Provider | Distance Apart | datetime_first | datetime_last | Licence Name | has_pm25 |
|---|---|---|---|---|---|---|
| 5754 | `caaqm` | 328.1 m (to 6957) | `2018-04-16T14:30:00Z` | `2018-05-12T06:30:00Z` | `unknown` | `True` |
| 6957 | `CPCB` | 328.1 m (to 5754) | `2018-08-10T06:00:00Z` | `2026-11-18T18:00:00Z` | `unknown` | `True` |

### Group `DUP-10`: major dhyan chand national stadium, delhi - dpcc
- **Stations in Group**: `2`
- **Maximum Distance Apart**: `282.6 m`

| Station ID | Provider | Distance Apart | datetime_first | datetime_last | Licence Name | has_pm25 |
|---|---|---|---|---|---|---|
| 5755 | `caaqm` | 282.6 m (to 6929) | `2018-04-26T23:00:00Z` | `2018-05-12T04:30:00Z` | `unknown` | `True` |
| 6929 | `CPCB` | 282.6 m (to 5755) | `2018-08-10T07:00:00Z` | `2026-11-18T18:00:00Z` | `unknown` | `True` |

### Group `DUP-11`: ashok vihar, delhi - dpcc
- **Stations in Group**: `2`
- **Maximum Distance Apart**: `52.2 m`

| Station ID | Provider | Distance Apart | datetime_first | datetime_last | Licence Name | has_pm25 |
|---|---|---|---|---|---|---|
| 5762 | `caaqm` | 52.2 m (to 8917) | `2018-04-16T15:00:00Z` | `2018-05-12T06:00:00Z` | `unknown` | `True` |
| 8917 | `CPCB` | 52.2 m (to 5762) | `2018-12-15T15:00:00Z` | `2026-11-18T18:00:00Z` | `unknown` | `True` |

### Group `DUP-12`: okhla phase-2, delhi - dpcc
- **Stations in Group**: `2`
- **Maximum Distance Apart**: `802.2 m`

| Station ID | Provider | Distance Apart | datetime_first | datetime_last | Licence Name | has_pm25 |
|---|---|---|---|---|---|---|
| 5765 | `caaqm` | 802.2 m (to 8239) | `2018-04-26T03:00:00Z` | `2018-05-13T10:00:00Z` | `unknown` | `True` |
| 8239 | `CPCB` | 802.2 m (to 5765) | `2018-08-22T11:45:00Z` | `2026-11-18T18:00:00Z` | `unknown` | `True` |

### Group `DUP-13`: nehru nagar, delhi - dpcc
- **Stations in Group**: `2`
- **Maximum Distance Apart**: `918.7 m`

| Station ID | Provider | Distance Apart | datetime_first | datetime_last | Licence Name | has_pm25 |
|---|---|---|---|---|---|---|
| 5766 | `caaqm` | 918.7 m (to 8365) | `2018-04-15T20:00:00Z` | `2018-05-13T10:00:00Z` | `unknown` | `True` |
| 8365 | `CPCB` | 918.7 m (to 5766) | `2018-08-10T06:00:00Z` | `2026-11-18T18:00:00Z` | `unknown` | `True` |

### Group `DUP-14`: murthal, sonipat - hspcb
- **Stations in Group**: `2`
- **Maximum Distance Apart**: `0.0 m`

| Station ID | Provider | Distance Apart | datetime_first | datetime_last | Licence Name | has_pm25 |
|---|---|---|---|---|---|---|
| 6951 | `CPCB` | 0.0 m (to 10906) | `2019-02-13T00:15:00Z` | `2026-11-18T18:00:00Z` | `unknown` | `True` |
| 10906 | `caaqm` | 0.0 m (to 6951) | `2020-01-02T08:00:00Z` | `2022-10-16T16:00:00Z` | `unknown` | `True` |

### Group `DUP-15`: shyam nagar, palwal - hspcb
- **Stations in Group**: `2`
- **Maximum Distance Apart**: `0.0 m`

| Station ID | Provider | Distance Apart | datetime_first | datetime_last | Licence Name | has_pm25 |
|---|---|---|---|---|---|---|
| 7280 | `CPCB` | 0.0 m (to 7281) | `2019-02-13T00:15:00Z` | `2026-11-18T18:00:00Z` | `unknown` | `True` |
| 7281 | `caaqm` | 0.0 m (to 7280) | `2020-01-01T10:15:00Z` | `2022-10-31T01:30:00Z` | `unknown` | `True` |

### Group `DUP-16`: east arjun nagar, delhi - cpcb
- **Stations in Group**: `2`
- **Maximum Distance Apart**: `876.3 m`

| Station ID | Provider | Distance Apart | datetime_first | datetime_last | Licence Name | has_pm25 |
|---|---|---|---|---|---|---|
| 7434 | `caaqm` | 876.3 m (to 8092) | `2018-08-10T06:00:00Z` | `2020-02-10T03:00:00Z` | `unknown` | `False` |
| 8092 | `caaqm` | 876.3 m (to 7434) | `2020-02-29T21:00:00Z` | `2022-01-26T07:00:00Z` | `unknown` | `False` |

### Group `DUP-17`: a-block sector 51 noida
- **Stations in Group**: `3`
- **Maximum Distance Apart**: `225.2 m`

| Station ID | Provider | Distance Apart | datetime_first | datetime_last | Licence Name | has_pm25 |
|---|---|---|---|---|---|---|
| 6551848 | `AirGradient` | 128.4 m (to 6551894); 225.2 m (to 6552066) | `2026-10-29T12:00:00Z` | `2026-11-18T01:00:00Z` | `CC BY 4.0` | `True` |
| 6551894 | `AirGradient` | 128.4 m (to 6551848); 219.1 m (to 6552066) | `unknown` | `unknown` | `CC BY 4.0` | `True` |
| 6552066 | `AirGradient` | 225.2 m (to 6551848); 219.1 m (to 6551894) | `unknown` | `unknown` | `CC BY 4.0` | `True` |

## 2. Same Name, Far Apart (> 1000 m)

These stations share identical normalised names but are located farther apart than `1000 m`. Per project rules, they are **not** treated as duplicates.

| Station ID | Normalised Name | Provider | Closest Counterpart | Distance Apart | datetime_last |
|---|---|---|---|---|---|
| 2503 | `shadipur, delhi - cpcb` | `CPCB` | Station 5630 | **1.05 km** | `2018-02-22T02:45:00Z` |
| 5630 | `shadipur, delhi - cpcb` | `CPCB` | Station 2503 | **1.05 km** | `2026-11-18T18:00:00Z` |
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
| 6314 | `nise gwal pahari, gurugram - imd` | `caaqm` | Station 10921 | **29.26 km** | `2018-11-16T04:00:00Z` |
| 10921 | `nise gwal pahari, gurugram - imd` | `CPCB` | Station 6314 | **29.26 km** | `2026-11-18T18:00:00Z` |

## 3. Decision Guidance for Candidates CSV
1. In candidates CSV, duplicates are tagged with `duplicate_group_id` and `dup_note`.
2. When deciding which station to keep in each duplicate group:
   - Prefer stations with active reporting (`datetime_last` in 2026).
   - Prefer reference-grade monitors (`is_monitor = True`).
   - Mark one as `use` and duplicates as `exclude` in `decision`.
3. The `decision` column remains empty for maintainer review.
