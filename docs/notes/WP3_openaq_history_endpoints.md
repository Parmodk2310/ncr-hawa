# OpenAQ v3 Observation History & Pilot Endpoints (WP3 Step 1)

This note documents the official OpenAQ v3 API endpoints, request/response structures, rate limits, date formats, and paging behavior required to ingest historical hourly $\text{PM}_{2.5}$ and $\text{PM}_{10}$ observations for Delhi-NCR monitoring stations.

All quotes are taken directly from the fetched public documentation pages at `docs.openaq.org` and the official OpenAPI specification at `api.openaq.org/openapi.json`. Any detail not explicitly confirmed in the documentation is explicitly marked as **[Unverified]**.

---

## 1. Documentation Sources Fetched & Verified

1. **Rate Limits & Headers**:  
   URL: `https://docs.openaq.org/using-the-api/rate-limits`  
   Page Title: `Rate limits | OpenAQ Docs`
2. **Pagination & Limits**:  
   URL: `https://docs.openaq.org/using-the-api/pagination`  
   Page Title: `Pagination | OpenAQ Docs`
3. **Dates, Datetimes & Timezones**:  
   URL: `https://docs.openaq.org/using-the-api/dates-datetimes`  
   Page Title: `Dates, times and timezones | OpenAQ Docs`
4. **Sensors Resource**:  
   URL: `https://docs.openaq.org/resources/sensors`  
   Page Title: `Sensors | OpenAQ Docs`
5. **Get Sensors by Location ID**:  
   URL: `https://docs.openaq.org/api/operations/sensors_get_v3_locations__locations_id__sensors_get`  
   Operation: `GET /v3/locations/{locations_id}/sensors`
6. **Measurements Resource**:  
   URL: `https://docs.openaq.org/resources/measurements`  
   Page Title: `Measurements | OpenAQ Docs`
7. **Get Hourly Measurements by Sensor ID**:  
   URL: `https://docs.openaq.org/api/operations/sensor_hourly_measurements_get_v3_sensors__sensors_id__hours_get`  
   Operation: `GET /v3/sensors/{sensors_id}/hours`
8. **Get Measurements Aggregated to Hourly by Sensor ID**:  
   URL: `https://docs.openaq.org/api/operations/sensor_measurements_aggregated_get_hourly_v3_sensors__sensors_id__measurements_hourly_get`  
   Operation: `GET /v3/sensors/{sensors_id}/measurements/hourly`
9. **Get Raw Measurements by Sensor ID**:  
   URL: `https://docs.openaq.org/api/operations/sensor_measurements_get_v3_sensors__sensors_id__measurements_get`  
   Operation: `GET /v3/sensors/{sensors_id}/measurements`
10. **OpenAPI Specification**:  
    URL: `https://api.openaq.org/openapi.json`

---

## 2. Endpoint Selection for Hourly $\text{PM}_{2.5}$ and $\text{PM}_{10}$ History

### Candidate Endpoints

1. **`GET /v3/sensors/{sensors_id}/hours`** (Recommended)
   - *Documentation Quote* (`https://docs.openaq.org/api/operations/sensor_hourly_measurements_get_v3_sensors__sensors_id__hours_get`):  
     > "Provides a list of hourly measurements by sensor ID. If a sensor is reporting at a higher frequency than hourly (e.g. one measurement every 10 minutes), this endpoint returns the precomputed average measurement value by the hour."
   - *Documentation Quote* (`https://docs.openaq.org/resources/measurements`):  
     > "The hours resource is the hourly average (mean) value of measurements. Note: Many sensors on the OpenAQ platform report hourly values. In the case where the upstream reporting period is hourly, the hours resource and measurements resource are equivalent."

2. **`GET /v3/sensors/{sensors_id}/measurements/hourly`** (On-the-fly aggregator)
   - *Documentation Quote* (`https://docs.openaq.org/api/operations/sensor_measurements_aggregated_get_hourly_v3_sensors__sensors_id__measurements_hourly_get`):  
     > "Provides a list of measurements aggregated to hourly values on the fly by sensor ID. For better performance but similar functionality, /sensors/{sensors_id}/hours is the recommended endpoint."
   - *Documentation Quote* (`https://docs.openaq.org/resources/measurements`):  
     > "A call to the /v3/sensors/{sensors_id}/measurements/hourly is functionally the same as /v3/sensors/{sensors_id}/hours. The /hours resource is the preferred option."

3. **`GET /v3/sensors/{sensors_id}/measurements`** (Raw measurements)
   - *Documentation Quote* (`https://docs.openaq.org/resources/measurements`):  
     > "The measurements resource is the original measurement value as reported by the upstream source."

### Recommendation

**Use `GET /v3/sensors/{sensors_id}/hours`**:
- Precomputed hourly rollup minimizes server-side aggregation overhead.
- Directly harmonizes reporting frequency whether the underlying station reports hourly (e.g. CPCB) or sub-hourly (e.g. AirGradient every 10 minutes).
- Specifically designated by OpenAQ documentation as the preferred endpoint.

### Prerequisite: Sensor Discovery via `GET /v3/locations/{locations_id}/sensors`

Because measurements in OpenAQ v3 are indexed by `sensors_id` rather than station/location ID, a station's sensors must first be queried via:
- **`GET /v3/locations/{locations_id}/sensors`**
- *Documentation Quote* (`https://docs.openaq.org/api/operations/sensors_get_v3_locations__locations_id__sensors_get`):  
  > "Provides a list of sensors by location ID"
- Each sensor in the returned `results` array provides:
  - `id`: integer (the `sensors_id`)
  - `parameter`: `{"id": <int>, "name": "pm25" | "pm10", "units": "µg/m³", ...}`
  - `datetimeFirst`, `datetimeLast`: period covered by the sensor.

---

## 3. Request Parameters & Rate Limiting

### Query Parameters for `GET /v3/sensors/{sensors_id}/hours`

Verified from `https://api.openaq.org/openapi.json` and `https://docs.openaq.org/api/operations/sensor_hourly_measurements_get_v3_sensors__sensors_id__hours_get`:

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `sensors_id` | path integer | **Yes** | — | "Limit the results to a specific sensors id" |
| `datetime_from` | query string (date-time or date) | No | `null` | "From when? e.g. 2022-10-01T11:19:38-06:00, 2022-10-01" |
| `datetime_to` | query string (date-time or date) | No | `null` | "To when? e.g. 2022-10-01T11:19:38-06:00, 2022-10-01" |
| `limit` | query integer | No | `100` | "Change the number of results returned. e.g. limit=100 will return up to 100 results" (up to 1,000) |
| `page` | query integer | No | `1` | "Paginate through results. e.g. page=1 will return first page of results" |

*Documentation Quote* (`https://docs.openaq.org/using-the-api/pagination`):  
> "For resources with a high volume of results, such as /measurements and /hours using the datetimeFrom and datetimeTo to limit to a single year or less is highly recommended. Querying the entire dataset and paging using the page query parameter alone can be slow. Adding a smaller time range allows the query to leverage database indexes and will generally result in more performant queries."

### Rate Limits & Headers

Verified from `https://docs.openaq.org/using-the-api/rate-limits`:

- **Tier (Free / General Use)**:
  - **60 requests / minute**
  - **2,000 requests / hour**
  - "API rate limits are scoped to the user API key."
- **Authentication**: Sent via `X-API-Key` HTTP header.
- **Rate Limit Response Headers**:
  - `x-ratelimit-limit`: "Specifies the maximum number of requests allowed within the current rate limit period."
  - `x-ratelimit-remaining`: "Indicates the number of requests remaining before reaching the rate limit."
  - `x-ratelimit-used`: "Shows the number of requests that have been made during the current rate limit period."
  - `x-ratelimit-reset`: "Provides a timestamp indicating when the rate limit period will reset."
- **Exceeding Limits**:
  - HTTP `429 Too Many Requests`.
  - *Documentation Quote*: "If a rate limit is exceeded, the API returns a 429 'Too many requests' HTTP status code. To continue, wait until the next rate limit period starts as described in OpenAQ's rate limit policy. Avoid making more requests during this time to prevent further errors."

---

## 4. Response Payload Structure

Verified from `https://docs.openaq.org/resources/measurements` and `https://docs.openaq.org/api/operations/sensor_hourly_measurements_get_v3_sensors__sensors_id__hours_get`:

### Top-Level Envelope
```json
{
  "meta": {
    "name": "openaq-api",
    "website": "/",
    "page": 1,
    "limit": 100,
    "found": 168
  },
  "results": [
    {
      "value": 43.5,
      "flagInfo": {
        "hasFlags": false
      },
      "parameter": {
        "id": 2,
        "name": "pm25",
        "units": "µg/m³",
        "displayName": "PM2.5"
      },
      "period": {
        "label": "1hour",
        "interval": "01:00:00",
        "datetimeFrom": {
          "utc": "2026-11-01T00:00:00Z",
          "local": "2026-11-01T05:30:00+05:30"
        },
        "datetimeTo": {
          "utc": "2026-11-01T01:00:00Z",
          "local": "2026-11-01T06:30:00+05:30"
        }
      },
      "coordinates": null,
      "summary": {
        "min": 40.0,
        "q02": 40.5,
        "q25": 42.0,
        "median": 43.5,
        "q75": 45.0,
        "q98": 46.5,
        "max": 47.0,
        "avg": 43.5,
        "sd": 2.1
      },
      "coverage": {
        "expectedCount": 1,
        "expectedInterval": "01:00:00",
        "observedCount": 1,
        "observedInterval": "01:00:00",
        "percentComplete": 100.0,
        "percentCoverage": 100.0,
        "datetimeFrom": {
          "utc": "2026-11-01T00:00:00Z",
          "local": "2026-11-01T05:30:00+05:30"
        },
        "datetimeTo": {
          "utc": "2026-11-01T01:00:00Z",
          "local": "2026-11-01T06:30:00+05:30"
        }
      }
    }
  ]
}
```

---

## 5. Date Fields (UTC vs Local) and Time Alignment

Verified from `https://docs.openaq.org/using-the-api/dates-datetimes`:

1. **Dual Representation in Payload**:
   - Every timestamp in `period.datetimeFrom`, `period.datetimeTo`, `coverage.datetimeFrom`, and `coverage.datetimeTo` is returned as a `DatetimeObject` containing both fields:
     ```json
     {
       "utc": "2019-07-11T20:00:00Z",
       "local": "2019-07-11T14:00:00-06:00"
     }
     ```
   - *Documentation Quote*: "To ensure timezones are clearly represented in results, the API returns a datetime object which includes both UTC time and local time."

2. **Time-Ending Convention**:
   - *Documentation Quote*:  
     > "Data on OpenAQ are harmonized to follow an exclusive time-ending standard. This means a time stamp for an hourly measurement 03:00 represents the data from 02:00 until 02:59."
     > "while a date marks the start of a specific day or year, a datetime indicates when that period has concluded."

3. **Query Format**:
   - *Documentation Quote*:  
     > "When requesting data from the OpenAQ API, timestamps should ideally include a timezone in the ISO-8601 format (e.g., 2024-08-25T15:00:00Z for UTC time). This ensures that the data retrieved accurately reflects the time it was recorded, regardless of the station’s location. If a timezone is not provided in the timestamp, the API automatically assumes the local time for the station where the data was collected."

---

## 6. How a No-Data Hour Appears

- In the OpenAPI schema (`HourlyData`), the `value` field is defined as nullable:
  `{"anyOf": [{"type": "number"}, {"type": "null"}]}`.
- In time-series databases like OpenAQ, when a sensor is offline or does not transmit observations for a given hour, no record is generated for that hour. The missing hour is **simply omitted from the `results` array** (sparse series).
- If a measurement was logged but flagged as invalid or uncalibrated by QA routines, an entry may appear with `value: null` and `flagInfo.hasFlags: true`.
- **[Unverified in public docs]**: The official documentation pages do not explicitly state whether missing hours are guaranteed to be omitted as gaps in the list or if dummy rows with `value: null` can be emitted. Downstream parsers must defensively handle both:
  1. Gaps in the timestamp sequence (sparse series), and
  2. Objects with `value is None` / `null`.
  *(In accordance with project rule 7: missing data must strictly map to `no_data`, never defaulting to 0 or "Good").*

---

## 7. How Paging Works

Verified from `https://docs.openaq.org/using-the-api/pagination`:

- Default page size: `limit=100`.
- Maximum page size: `limit=1000`.
- Page parameter: `page=1`, `page=2`, etc.
- Result set count: Available in `meta.found` (can be an integer, a string like `">1000"`, or `null`).
- End-of-pagination condition:
  Paging stops when `results` array is empty (`len(results) == 0`) or has fewer items than `limit` (`len(results) < limit`), or when all `found` items have been collected.

---

## 8. Request Budget: How Many Requests for One Station-Week

A station-week spans 7 days $\times$ 24 hours/day = **168 hourly records** per sensor parameter.

1. **Hourly Data Requests**:
   - **With `limit=1000`**: 168 records fit comfortably within a single response page (since $168 \le 1000$).
     - $\text{PM}_{2.5}$: **1 request**
     - $\text{PM}_{10}$: **1 request**
     - Subtotal: **2 requests** per station-week.
   - **With `limit=100` (default)**:
     - 168 records require $\lceil 168 / 100 \rceil = 2$ pages per sensor.
     - $\text{PM}_{2.5}$: **2 requests**
     - $\text{PM}_{10}$: **2 requests**
     - Subtotal: **4 requests** per station-week.

2. **Sensor Discovery**:
   - Initial call to `GET /v3/locations/{locations_id}/sensors`: **1 request** per station (can be cached).

3. **Total Budget**:
   - For 1 station over 1 week: **3 requests** (with `limit=1000`, including sensor discovery) or **2 requests** (if sensor IDs are pre-cached).
   - For all 5 pilot stations over 1 week:
     - 5 discovery requests + $5 \times 2$ data requests = **15 requests total**.
     - Well within OpenAQ's free limit of 60 requests/minute and 2,000 requests/hour.

---

## 9. Pilot Station Selection

### Selection Rule
From the prompt instructions:
1. Source: `data/stations_candidates.csv`
2. Criteria: `decision == "use"` and `has_pm25 == "yes"` (in `stations_candidates.csv`, `has_pm25` is boolean `'True'`).
3. Allocation: One station per `area_id` across the five areas (`central_delhi`, `faridabad`, `ghaziabad`, `gurugram`, `noida`).
4. Ranking within area: Station with the **latest `datetime_last`**; ties broken by **lowest `station_id`**.

### Selected Five Pilot Stations (Approved by Maintainer)

| Area ID | Station ID | Station Name | Provider | `datetime_last` (UTC) | PM2.5 Sensor | PM10 Sensor |
|---|---|---|---|---|---|---|
| `central_delhi` | **8118** | New Delhi | AirNow | `2026-11-18T20:30:00Z` | `23534` | *None (skipped)* |
| `faridabad` | **6934** | Dr. Karni Singh Shooting Range, Delhi - DPCC | CPCB | `2026-11-18T18:00:00Z` | `12235011` | `12235010` |
| `ghaziabad` | **235** | Anand Vihar, New Delhi - DPCC | CPCB | `2026-11-18T18:00:00Z` | `12235610` | `12235609` |
| `gurugram` | **301** | Vikas Sadan, Gurugram - HSPCB | CPCB | `2026-11-18T18:00:00Z` | `14258988` | `14258987` |
| `noida` | **5598** | Sector - 125, Noida, UP - UPPCB | CPCB | `2026-11-18T18:00:00Z` | `12235187` | `12235186` |

*Note on Selection*:
Stations 301 and 5598 were chosen by the maintainer to ensure CPCB reference-grade monitors with active coverage for both $\text{PM}_{2.5}$ and $\text{PM}_{10}$ in Gurugram and Noida (in place of AirGradient devices that only report $\text{PM}_{2.5}$). Both have confirmed `decision == "use"`, active $\text{PM}_{2.5}$ and $\text{PM}_{10}$ sensors in raw location files, and `datetime_last` within 3 days (< 30 days).

---

## 10. Critical Implementation Notes for Step 2

1. **Parameter Availability ($\text{PM}_{10}$)**:
   - Stations `6934` (Faridabad), `235` (Ghaziabad), `301` (Gurugram), and `5598` (Noida) report **both** $\text{PM}_{2.5}$ and $\text{PM}_{10}$.
   - Station `8118` (Central Delhi, AirNow US Embassy) reports **only** $\text{PM}_{2.5}$ (sensor id `23534`); it has no $\text{PM}_{10}$ sensor. As instructed, the ingestion pipeline skips $\text{PM}_{10}$ for station 8118 and reports `"no PM10 sensor"` in the run summary rather than logging a failure.
2. **Multiple Sensors per Parameter on CPCB Stations**:
   - Stations `235`, `6934`, and `301` have both legacy OpenAQ v2 sensor IDs and modern OpenAQ v3 sensor IDs. The pipeline maps and targets the modern v3 sensor IDs.
3. **Throttling & Guardrails**:
   - Maintain $\ge 1.1\text{ s}$ sleep between requests to comply with the 60 requests/minute rate limit.
   - Parse `x-ratelimit-remaining` and `x-ratelimit-reset` headers on each response.
   - Back off on HTTP 429 and 5xx; fail immediately without leaking secrets on HTTP 401.
   - Hard request cap via `--max-requests` (default 60) with warning output on cutoff.
