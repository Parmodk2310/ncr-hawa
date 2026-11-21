# Station Decision Summary Report (Task A-003d)

## 1. Decision Mapping Table
Decisions were populated directly from `proposed_decision` according to the approved rule mappings below.

| Proposed Decision | Applied Decision | Description / Policy |
|---|---|---|
| `use` | `use` | Active monitor used in forecast model training and evaluation |
| `history_only` | `history_only` | Inactive station or older duplicate; retained for historical reference only |
| `exclude` | `exclude` | Excluded from pipeline (e.g. no verified PM2.5 capability) |
| `review` | `review` | Unresolved station pending manual investigation; NOT converted to exclude |

> [!IMPORTANT]
> **Safety & Policy Guardrails**:
> - **No 'publish' in decision**: `decision` is strictly limited to `use`, `history_only`, `exclude`, or `review`. It is **never** set to `publish`.
> - **Protected Columns**: `publish_candidate`, `proposed_decision`, and `proposed_reason` are never modified by this script.
> - **Skip-if-nonempty**: Any station row where `decision` was already non-empty was refused overwrite and preserved as-is.

## 2. Decision Application Summary
- **Total candidate stations**: 119
- **Decisions newly applied**: 119
- **Pre-existing decisions skipped**: 0

## 3. Decision Counts by Area
| Area ID | Area Name | `use` | `history_only` | `review` | `exclude` | Total |
|---|---|---|---|---|---|---|
| `central_delhi` | Central Delhi | 40 | 20 | 6 | 2 | **68** |
| `faridabad` | Faridabad | 5 | 3 | 0 | 0 | **8** |
| `ghaziabad` | Ghaziabad | 11 | 3 | 2 | 0 | **16** |
| `gurugram` | Gurugram | 11 | 0 | 4 | 0 | **15** |
| `noida` | Noida | 9 | 0 | 3 | 0 | **12** |
| **Total** | **All Areas** | **76** | **26** | **15** | **2** | **119** |

## 4. Stations Pending Review (`decision = review`)
Stations marked `review` remain unresolved and require manual investigation. They are **not** turned into `exclude`.

| Station ID | Station Name | Provider | Area ID | Proposed Reason |
|---|---|---|---|---|
| `15` | IGI Airport | CPCB | `central_delhi` | last date unknown |
| `16` | Civil Lines | CPCB | `central_delhi` | last date unknown |
| `5509` | Anand Vihar, Delhi - DPCC | caaqm | `ghaziabad` | same-provider cluster, check if separate devices |
| `5743` | Rohini, Delhi - DPCC | caaqm | `central_delhi` | same name far apart, check coordinates |
| `5759` | Sonia Vihar, Delhi - DPCC | caaqm | `central_delhi` | same name far apart, check coordinates |
| `5760` | Dwarka-Sector 8, Delhi - DPCC | caaqm | `gurugram` | same name far apart, check coordinates |
| `6314` | NISE Gwal Pahari, Gurugram - IMD | caaqm | `gurugram` | same name far apart, check coordinates |
| `6931` | Dwarka-Sector 8, Delhi - DPCC | CPCB | `gurugram` | same name far apart, check coordinates |
| `8475` | Sonia Vihar, Delhi - DPCC | CPCB | `central_delhi` | same name far apart, check coordinates |
| `10487` | Anand Vihar, Delhi - DPCC | caaqm | `ghaziabad` | same-provider cluster, check if separate devices |
| `10831` | Rohini, Delhi - DPCC | CPCB | `central_delhi` | same name far apart, check coordinates |
| `10921` | NISE Gwal Pahari, Gurugram - IMD | CPCB | `gurugram` | same name far apart, check coordinates |
| `6551848` | A-Block Sector 51 NOIDA | AirGradient | `noida` | same-provider cluster, check if separate devices |
| `6551894` | A-Block Sector 51 NOIDA | AirGradient | `noida` | same-provider cluster, check if separate devices |
| `6552066` | A-Block Sector 51 NOIDA | AirGradient | `noida` | same-provider cluster, check if separate devices |
