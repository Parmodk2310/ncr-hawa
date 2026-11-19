# Proposed Station Decisions Report (Task A-003c)

## Overview & Decision Rules
- **Input Licences File**: `data/licences.csv`
- **Duplicate Threshold for Proposals (`--proposal-dup-m`)**: `500 m` (maintainer guess)
- **Reference UTC Date**: `2026-11-19`
- **Active Cutoff Date (30 days)**: `2026-10-20`
- **Total Candidate Locations**: `119`

### Decision Rules Hierarchy
Duplicate detection threshold feeding these proposals is `500 m`.
The following rules were applied in strict sequential order:

| Rule # | Condition | Proposed Decision | Proposed Reason | Priority / Notes |
|---|---|---|---|---|
| **1** | `has_pm25` is `no` or unknown | `exclude` | `no PM2.5` | Highest priority |
| **5** | Same name as another station > 5 km apart | `review` | `same name far apart, check coordinates` | **Overrides rules 3 & 4** |
| **3** | In duplicate group (same provider) | `review` | `same-provider cluster, check if separate devices` | Rule 3 exception: never marked `history_only` |
| **3** | In duplicate group (different providers) | `use` (active) / `history_only` (inactive) | `active monitor` / `no data in 30 days` | Other members: `older duplicate of <id>` |
| **2** | `datetime_last` missing / invalid | `review` | `last date unknown` | Evaluated before recency |
| **4** | `datetime_last` older than 30 days | `history_only` | `no data in 30 days` | Inactive historical stations |
| **6** | Everything else | `use` | `active monitor` | Default for active valid monitors |

> [!IMPORTANT]
> **Publishing Policy Note (`AQ_11`)**:
> `proposed_decision` is **never** set to `publish`.
> A separate column `publish_candidate = yes` is set **only if** `redistributionAllowed` is `True`,
> `licence_name` is non-blank, and `proposed_decision` is `use`.
> **This does NOT mean publishing is allowed until the maintainer has read and verified the licence text.**

## 1. Summary of Proposed Decisions
| Proposed Decision | Station Count | Share | Description |
|---|---|---|---|
| `use` | 76 | 63.9% | Active monitors recommended for forecast training/evaluation |
| `history_only` | 26 | 21.8% | Inactive (> 30 days) or older duplicates of active stations |
| `review` | 15 | 12.6% | Stations with same name > 5 km apart, missing dates, or clusters |
| `exclude` | 2 | 1.7% | Stations without confirmed PM2.5 capability |
| **Total** | **119** | **100.0%** | All candidate stations within radius |

- **Publish Candidates (`publish_candidate = yes`)**: **10** (8.4%)
- **Non-Publish Candidates (`publish_candidate = no`)**: **109** (91.6%)

## 2. Proposed Decisions by Forecast Area
| Area ID | Area Name | `use` | `history_only` | `review` | `exclude` | Total |
|---|---|---|---|---|---|---|
| `central_delhi` | Central Delhi | 40 | 20 | 6 | 2 | **68** |
| `noida` | Noida | 9 | 0 | 3 | 0 | **12** |
| `gurugram` | Gurugram | 11 | 0 | 4 | 0 | **15** |
| `ghaziabad` | Ghaziabad | 11 | 3 | 2 | 0 | **16** |
| `faridabad` | Faridabad | 5 | 3 | 0 | 0 | **8** |

## 3. Stations Requiring Manual Review (`review`)
Total stations flagged for review: **15**

| Station ID | Name | Area ID | Distance (km) | Reason | datetime_last |
|---|---|---|---|---|---|
| 15 | IGI Airport | `central_delhi` | 12.62 | `last date unknown` | `unknown` |
| 16 | Civil Lines | `central_delhi` | 7.80 | `last date unknown` | `unknown` |
| 5509 | Anand Vihar, Delhi - DPCC | `ghaziabad` | 10.47 | `same-provider cluster, check if separate devices` | `2022-10-31T00:30:00Z` |
| 5743 | Rohini, Delhi - DPCC | `central_delhi` | 20.78 | `same name far apart, check coordinates` | `2018-05-12T06:30:00Z` |
| 5759 | Sonia Vihar, Delhi - DPCC | `central_delhi` | 11.49 | `same name far apart, check coordinates` | `2018-05-12T05:00:00Z` |
| 5760 | Dwarka-Sector 8, Delhi - DPCC | `gurugram` | 23.25 | `same name far apart, check coordinates` | `2018-05-12T05:00:00Z` |
| 6314 | NISE Gwal Pahari, Gurugram - IMD | `gurugram` | 18.11 | `same name far apart, check coordinates` | `2018-11-16T04:00:00Z` |
| 6931 | Dwarka-Sector 8, Delhi - DPCC | `gurugram` | 13.01 | `same name far apart, check coordinates` | `2026-11-18T18:00:00Z` |
| 8475 | Sonia Vihar, Delhi - DPCC | `central_delhi` | 11.82 | `same name far apart, check coordinates` | `2026-11-18T18:00:00Z` |
| 10487 | Anand Vihar, Delhi - DPCC | `ghaziabad` | 10.47 | `same-provider cluster, check if separate devices` | `2021-09-20T07:45:00Z` |
| 10831 | Rohini, Delhi - DPCC | `central_delhi` | 16.21 | `same name far apart, check coordinates` | `2026-11-18T18:00:00Z` |
| 10921 | NISE Gwal Pahari, Gurugram - IMD | `gurugram` | 12.35 | `same name far apart, check coordinates` | `2026-11-18T18:00:00Z` |
| 6551848 | A-Block Sector 51 NOIDA | `noida` | 4.95 | `same-provider cluster, check if separate devices` | `2026-11-18T01:00:00Z` |
| 6551894 | A-Block Sector 51 NOIDA | `noida` | 5.08 | `same-provider cluster, check if separate devices` | `unknown` |
| 6552066 | A-Block Sector 51 NOIDA | `noida` | 5.03 | `same-provider cluster, check if separate devices` | `unknown` |

## 4. Preliminary Publish Candidates (`publish_candidate = yes`)
Total publish candidate stations: **10**

> [!NOTE]
> All other stations (109) have `redistributionAllowed = unknown` or blank licences;
> internal use of unlicensed stations is unverified.

| Station ID | Name | Provider | Licence Name | redistributionAllowed |
|---|---|---|---|---|
| 8118 | New Delhi | `AirNow` | `US Public Domain` | `True` |
| 2860223 | GK1 (Oberoi Terrace) | `AirGradient` | `CC BY 4.0` | `True` |
| 3024966 | NASA GSFC Rutgers Calib. N8 | `Clarity` | `CC0 1.0` | `True` |
| 4663956 | Santushti Apartments, Vasant Kunj | `AirGradient` | `CC BY 4.0` | `True` |
| 4712609 | Air Check | `AirGradient` | `CC BY 4.0` | `True` |
| 6105800 | Sector 1, Noida extension | `AirGradient` | `CC BY 4.0` | `True` |
| 6125489 | Uptitude Cloud Pvt Ltd - Sector 62, GGN | `AirGradient` | `CC BY 4.0` | `True` |
| 6145551 | Anand Lok | `AirGradient` | `CC BY 4.0` | `True` |
| 6551511 | Sector-26, Noida | `AirGradient` | `CC BY 4.0` | `True` |
| 6551581 | Anahad Foundation | `AirGradient` | `CC BY 4.0` | `True` |

## 5. Next Steps for Maintainer
1. Open `data/stations_candidates.csv`.
2. Inspect the `review` stations in Section 3 and confirm GPS coordinates.
3. Copy or adjust `proposed_decision` values into the official `decision` column (`use` or `exclude`).
4. Leave `decision` empty for any station still under verification.
