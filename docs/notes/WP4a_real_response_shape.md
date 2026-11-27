# Real OpenAQ Hourly Response Shape (WP4a Step 1)

This note documents the actual structure, data types, and empirical behavior observed in the real OpenAQ v3 historical hourly observation JSON files stored under `data/raw/openaq/`.

---

## 1. Real Metadata and Results Schema

### Top-Level Envelope
The root JSON object contains exactly two keys:
1. `meta`: An object containing query pagination and result metadata.
2. `results`: An array of observation objects.

### `meta` Fields and Data Types
| Field Name | Data Type | Example Value | Description |
|---|---|---|---|
| `name` | `str` | `"openaq-api"` | API service name |
| `website` | `str` | `"/"` | API reference root |
| `page` | `int` | `1` | 1-based page index |
| `limit` | `int` | `1000` | Requested page size limit |
| `found` | **`int`** | `306`, `312`, `314` | **Integer** representing total matching records (never a string `">1000"` or `null` in these real responses) |

### `results[]` Item Fields and Data Types
Every record across all 18 real raw files (5,488 records total) has the identical set of 7 top-level keys:
- `value`: `float` (e.g. `196.0`, `43.2`).
- `flagInfo`: `dict` with key `hasFlags` (`bool`).
- `parameter`: `dict` containing:
  - `id`: `int` (e.g. `1` for $\text{PM}_{10}$, `2` for $\text{PM}_{2.5}$)
  - `name`: `str` (`"pm10"` or `"pm25"`)
  - `units`: `str` (`"µg/m³"`)
  - `displayName`: `null` (observed as `None` across all real files)
- `period`: `dict` containing:
  - `label`: `str` (`"1hour"`)
  - `interval`: `str` (`"01:00:00"`)
  - `datetimeFrom`: `dict` with `utc` (`str`) and `local` (`str`)
  - `datetimeTo`: `dict` with `utc` (`str`) and `local` (`str`)
- `coordinates`: `null` (stationary monitoring stations)
- `summary`: `dict` containing summary stats: `min` (`float`), `q02` (`float`), `q25` (`float`), `median` (`float`), `q75` (`float`), `q98` (`float`), `max` (`float`), `avg` (`float`), `sd` (`float` or `null`)
- `coverage`: `dict` containing completeness stats: `expectedCount` (`int`), `expectedInterval` (`str`), `observedCount` (`int`), `observedInterval` (`str`), `percentComplete` (`float`), `percentCoverage` (`float`), `datetimeFrom` (`dict`), `datetimeTo` (`dict`)

---

## 2. Period Start and End Timestamps (UTC and Local)

In each record:
- **Period Start**:
  - `r["period"]["datetimeFrom"]["utc"]`: e.g. `"2026-10-31T23:30:00Z"`
  - `r["period"]["datetimeFrom"]["local"]`: e.g. `"2026-11-01T05:00:00+05:30"`
- **Period End**:
  - `r["period"]["datetimeTo"]["utc"]`: e.g. `"2026-11-01T00:30:00Z"`
  - `r["period"]["datetimeTo"]["local"]`: e.g. `"2026-11-01T06:00:00+05:30"`

### Critical Timing Observation: The Half-Hour Offset
In the Indian monitoring network (CPCB and DPCC), stations report hourly cycles aligned to **local clock hours** in Indian Standard Time ($\text{IST} = \text{UTC}+05:30$), for example from `05:00 IST` to `06:00 IST`.
Because the IST timezone offset is an odd half-hour (`+05:30`), the corresponding UTC timestamps end at **`:30:00Z`**:
- `05:00:00+05:30` $\Longleftrightarrow$ `23:30:00Z` (nominal start)
- `06:00:00+05:30` $\Longleftrightarrow$ `00:30:00Z` (nominal end)

All timestamps adhere to OpenAQ's **time-ending convention**: a record with end time `00:30:00Z` (`06:00:00 IST`) covers the preceding hour (`23:30:00Z` to `00:30:00Z`, i.e., `05:00` to `05:59` IST).

---

## 3. Units, Null Values, and Missing Hours

- **Unit**: `"µg/m³"` (micrograms per cubic meter, using Unicode micro sign `\u00b5`).
- **Null Values**: **0 null values** across all 5,488 records in all 18 raw files. Every returned record has a numeric `float` value.
- **Missing Hours (Gaps)**: **Yes, missing hours occur across all stations.** Missing hours are represented as **omissions from the results list** (sparse time series), rather than records with `null` values. For example, station 235 has a 20-hour gap from `2026-11-03T07:30:00Z` to `2026-11-04T03:30:00Z`. Station 5598 has 15 distinct gaps (up to 20 hours).
- **Disagreements Between Fetches**: Comparing the two fetch timestamps (`20261126T130746Z` and `20261127T231902Z`) across all common timestamps yielded **0 disagreements** (100% agreement on identical timestamps).

---

## 4. Truncated Real Example

Taken directly from `data/raw/openaq/235/12235610/20261126T130746Z_p1.json`:

```json
{
  "meta": {
    "name": "openaq-api",
    "website": "/",
    "page": 1,
    "limit": 1000,
    "found": 313
  },
  "results": [
    {
      "value": 145.0,
      "flagInfo": {
        "hasFlags": false
      },
      "parameter": {
        "id": 2,
        "name": "pm25",
        "units": "µg/m³",
        "displayName": null
      },
      "period": {
        "label": "1hour",
        "interval": "01:00:00",
        "datetimeFrom": {
          "utc": "2026-10-31T23:30:00Z",
          "local": "2026-11-01T05:00:00+05:30"
        },
        "datetimeTo": {
          "utc": "2026-11-01T00:30:00Z",
          "local": "2026-11-01T06:00:00+05:30"
        }
      },
      "coordinates": null,
      "summary": {
        "min": 140.0,
        "q02": 140.0,
        "q25": 140.0,
        "median": 145.0,
        "q75": 150.0,
        "q98": 150.0,
        "max": 150.0,
        "avg": 145.0,
        "sd": 7.0710678118654755
      },
      "coverage": {
        "expectedCount": 4,
        "expectedInterval": "01:00:00",
        "observedCount": 4,
        "observedInterval": "01:00:00",
        "percentComplete": 100.0,
        "percentCoverage": 100.0,
        "datetimeFrom": {
          "utc": "2026-10-31T22:45:00Z",
          "local": "2026-11-01T04:15:00+05:30"
        },
        "datetimeTo": {
          "utc": "2026-11-01T00:30:00Z",
          "local": "2026-11-01T06:00:00+05:30"
        }
      }
    }
  ]
}
```

---

## 5. Differences from `docs/notes/WP3_openaq_history_endpoints.md`

| Aspect | WP3 Notes (Documentation Spec) | Real Observed Data (WP4a) |
|---|---|---|
| `meta.found` type | Documented as `Any of: integer, string, null` (e.g. `">1000"`) | Consistently an **`int`** across all pilot files (e.g. 312, 313) |
| UTC Timestamps | Hypothetical examples assumed top-of-hour (`:00:00Z`) | Real timestamps end at **`:30:00Z`** because local cycles align with IST (`UTC+05:30`) |
| Missing Hours Representation | Noted as unverified whether missing hours emit `value: null` or are omitted | Missing hours are **completely omitted** from `results` (sparse series); 0 null values exist |
| `parameter.displayName` | Documented as string or null | Consistently `null` in real data |
| `coverage.datetimeFrom` | In synthetic docs assumed equal to `period.datetimeFrom` | Often starts 45 minutes prior (e.g. `22:45:00Z` for sub-hourly rolling observations) |
| Coordinates | Documented as optional coordinates object | Always `null` for fixed stationary monitors |
