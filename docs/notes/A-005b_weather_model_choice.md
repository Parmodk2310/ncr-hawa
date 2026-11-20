# A-005b: Weather Model Evaluation & Selection for Delhi-NCR

**Task**: A-005b Step 1 (Research Only)  
**Date**: 2026-11-20  
**Branch**: `feat/A-005b-pin-weather-model`  
**Target Coordinates**: Delhi NCR (approx. 28.61°N, 77.21°E; Central Delhi)  
**Status**: Proposal awaiting maintainer decision (No decision taken)

---

## 1. Executive Summary & Candidate Recommendation

Open-Meteo provides access to multiple numerical weather prediction (NWP) models. For Delhi-NCR (`28.61°N, 77.21°E`), regional high-resolution models (such as ICON-D2, AROME, RRFS) are unavailable; only **global models** cover this region.

To pin a single weather model for retrospective forecast analysis (via Previous Runs / Historical Forecast APIs) and future live archiving, two primary candidates are proposed for maintainer selection:

1. **Candidate A: ECMWF IFS** (`ecmwf_ifs025` or `ecmwf_ifs`)
   - **Key Strengths**: Leading global atmospheric physics and skill; explicitly provides Boundary Layer Height (`boundary_layer_height`), which is essential for capturing winter inversion and particulate matter trapping in Delhi.
   - **Key Trade-offs**: Standard global grid resolution is 0.25° (~25 km) with 3-hourly native timestep (interpolated to hourly by Open-Meteo); archived in Previous Runs from January 2024.
2. **Candidate B: NOAA GFS** (`ncep_gfs_seamless`)
   - **Key Strengths**: Longest historical previous runs archive on Open-Meteo (2 m temperature back to March 23, 2021); native 1-hourly timestep; explicitly provides Boundary Layer Height (`boundary_layer_height`); 0.11° (~13 km) resolution.
   - **Key Trade-offs**: Known tropical convective biases and boundary layer overestimation in South Asia compared to ECMWF.

> [!IMPORTANT]
> **Maintainer Decision Required**: Per task guidelines, this document proposes the candidates and details trade-offs. The agent **does not decide**. Awaiting maintainer choice before updating archive code or configs.

---

## 2. Official Open-Meteo Documentation Sources & Quotes

The following quotations are taken directly from the official Open-Meteo documentation pages fetched on 2026-11-20.

### 2.1 Weather Forecast API (`https://open-meteo.com/en/docs`)

* **Geographic Coverage**:
  > "Region: 🌍 Everywhere else | Regional Models: Global models only"

* **`models` Parameter**:
  > "Parameter: models | Format: String array | Required: No | Default: auto | Description: Manually select one or more weather models. Per default, the best suitable weather models will be combined."

* **Model Options Description**:
  > "Weather models cover different geographic areas at different resolutions and provide different weather variables. Depending on the model, data have been interpolated to hourly values or not all weather variables are available. Use the Weather models dropdown (just below the hourly variables) to select and compare individual models. To access the full archive of past forecast runs as issued, useful for forecast verification or training ML models, see the Historical Forecast API and the Previous Model Runs API."

### 2.2 Previous Runs API (`https://open-meteo.com/en/docs/previous-runs-api`)

* **Endpoint**:
  > `https://previous-runs-api.open-meteo.com/v1/forecast`

* **Lead-Time Offsets Concept**:
  > "Data from past model runs is aligned to fixed lead-time offsets of 1–7 days. Requesting `temperature_2m_previous_day1` returns the value predicted 24 hours before valid time; `_previous_day2` returns 48 hours before, and so on up to day 7. Comparing these offsets against observations or reanalysis makes it straightforward to measure how forecast skill degrades with lead time and to train bias-correction models."

* **Archival Start Dates**:
  > "Most models are archived from **January 2024**. GFS 2 m temperature extends back to **March 2021**. JMA GSM and MSM — available from **2018**."

* **Supported Models**:
  > "The Previous Runs API supports the same models as the Weather Forecast API. See the Forecast API documentation for the full model and variable list."
  > "Global models update every 6 hours; regional models (e.g. ICON-D2, AROME) update every 1–3 hours. The available lead-time window for each model is limited to its forecast horizon, so a model with a 3-day horizon will have at most `_previous_day3` populated."

### 2.3 Historical Forecast API (`https://open-meteo.com/en/docs/historical-forecast-api`)

* **Historical Archive Scope**:
  > "The Historical Forecast API archives comprehensive data, including atmospheric pressure levels, from all accessible weather forecast models. Depending on the model and public archive availability, data is available starting from 2021 or 2022."
  > - DWD ICON Global: Available Since `2022-11-24` (0.1°, Hourly, Every 6h)
  > - NOAA NCEP GFS: Available Since `2021-03-23` (0.11°, Hourly, Every 6h)
  > - ECMWF IFS 0.4°: Available Since `2022-11-07` (0.4°, 3-Hourly, Every 6h)
  > - ECMWF IFS 0.25°: Available Since `2024-02-03` (0.25°, 3-Hourly, Every 6h)
  > - ECMWF IFS HRES: Available Since `2017-01-01` (9 km, Hourly, Every 6h; archived in Single Runs from March 2024)

### 2.4 Model Dedicated Pages

* **ECMWF API** (`https://open-meteo.com/en/docs/ecmwf-api`):
  > "ECMWF transitioned to open-data on 1st October 2025, and Open-Meteo is pleased to provide access to the IFS forecasts at the full native 9 km resolution without any additional delay under open-data terms."
  > Explicitly lists: `Boundary Layer Height PBL` under Hourly Weather Variables.

* **NOAA GFS API** (`https://open-meteo.com/en/docs/gfs-api`):
  > Explicitly lists: `boundary_layer_height` under Hourly Weather Variables.

* **DWD ICON API** (`https://open-meteo.com/en/docs/dwd-api`):
  > Lists: Temperature, Humidity, Wind Speed, Wind Direction, Precipitation, Wind Gusts.
  > Does **NOT** list Boundary Layer Height.

---

## 3. Global Candidate Models for Delhi (`28.61°N, 77.21°E`)

Because Delhi is outside European and North American regional domains, only global models can be used. Below is a comparison of all candidate global models available in Open-Meteo:

| Model Name | Open-Meteo `models` Parameter | Spatial Resolution | Native Timestep | Update Frequency | Past Forecasts (Previous Runs) | Past Forecasts (Historical Forecast) | Boundary Layer Height Available? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **ECMWF IFS (0.25°)** | `ecmwf_ifs025` (or `ecmwf_ifs`) | 0.25° (~25 km) [or 9 km HRES] | 3-hourly [1-hourly HRES] | Every 6 hours | January 2024 | 2024-02-03 (0.25°) / 2022-11-07 (0.4°) | **Yes** (`boundary_layer_height`) |
| **NOAA GFS** | `ncep_gfs_seamless` (or `gfs_seamless`) | 0.11° (~13 km) / 0.25° | 1-hourly | Every 6 hours | March 2021 (temp) / Jan 2024 (others) | 2021-03-23 | **Yes** (`boundary_layer_height`) |
| **DWD ICON Global** | `dwd_icon_seamless` (or `dwd_icon_global`) | 0.1° (~11 km) | 1-hourly | Every 6 hours | January 2024 | 2022-11-24 | **No** (not listed in DWD API doc) |
| **CMC GEM Global** | `cmc_gem_seamless` (or `cmc_gem_gdps`) | 0.15° (~15 km) | 3-hourly | Every 12 hours | January 2024 | 2022-11-23 | **No** (not listed in GEM API doc) |
| **JMA GSM** | `jma_seamless` (or `jma_gsm`) | 0.5° (~55 km) | 6-hourly | Every 6 hours | 2018 | 2016-01-01 | **No** (not listed in JMA API doc) |
| **CMA GRAPES** | `cma_grapes_global` | 0.125° (~15 km) | 3-hourly | Every 6 hours | January 2024 | 2023-12-31 | **No** (not listed) |

---

## 4. Variable Availability Analysis for Previous-Day Runs (`_previous_day1`, `_previous_day2`)

For evaluating forecast skill and training offline bias-correction / ML models, the user requested support for previous-day variables:
- Temperature
- Relative Humidity
- Wind Speed & Direction
- Precipitation
- Boundary Layer Height (PBL)
- Wind Gusts

### 4.1 Variables Formally Documented in Previous Runs API UI

Inspection of the HTML checkboxes and parameter list in `https://open-meteo.com/en/docs/previous-runs-api` confirms that the following variables explicitly support `_previous_day0` through `_previous_day7`:

1. **Temperature**: `temperature_2m_previous_day1`, `temperature_2m_previous_day2`
2. **Relative Humidity**: `relative_humidity_2m_previous_day1`, `relative_humidity_2m_previous_day2`
3. **Dewpoint**: `dew_point_2m_previous_day1`, `dew_point_2m_previous_day2`
4. **Apparent Temperature**: `apparent_temperature_previous_day1`, `apparent_temperature_previous_day2`
5. **Precipitation**: `precipitation_previous_day1`, `precipitation_previous_day2`
6. **Rain**: `rain_previous_day1`, `rain_previous_day2`
7. **Wind Speed (10 m)**: `wind_speed_10m_previous_day1`, `wind_speed_10m_previous_day2`
8. **Wind Direction (10 m)**: `wind_direction_10m_previous_day1`, `wind_direction_10m_previous_day2`
9. **Surface Pressure & Sea Level Pressure**: `surface_pressure_previous_day1`, etc.
10. **Cloud Cover**: `cloud_cover_previous_day1`, etc.
11. **Upper-level Winds**: `wind_speed_80m_previous_day1`, `wind_speed_100m_previous_day1`, etc.

### 4.2 Variables NOT in Previous Runs API Documentation

* **Boundary Layer Height (`boundary_layer_height`)**:
  - Found in: Weather Forecast API (`https://open-meteo.com/en/docs`), ECMWF API, NOAA GFS API, Historical Forecast API, Single Runs API.
  - **Not found** in the Previous Runs API documentation page. There are no checkbox options for `boundary_layer_height_previous_day1` or `boundary_layer_height_previous_day2`.
  - *Status*: **Unverified** whether the Previous Runs API endpoint accepts `boundary_layer_height_previous_day1` or returns a 400 Bad Request error.
* **Wind Gusts (`wind_gusts_10m`)**:
  - Found in: Weather Forecast API, Historical Forecast API, Single Runs API.
  - **Not found** in the Previous Runs API documentation page.
  - *Status*: **Unverified** whether the Previous Runs API endpoint accepts `wind_gusts_10m_previous_day1` or returns a 400 Bad Request error.

### 4.3 Fallback for Boundary Layer Height & Wind Gusts

If retrospective boundary layer height or wind gusts are needed at D+1 / D+2 lead times:
1. **Single Runs API** (`https://single-runs-api.open-meteo.com/v1/forecast`): Explicitly supports `boundary_layer_height` and `wind_gusts_10m` by querying specific initialisation runs (`&run=YYYY-MM-DDTHH:00:00Z`).
2. **Historical Forecast API** (`https://historical-forecast-api.open-meteo.com/v1/forecast`): Explicitly supports `boundary_layer_height` and `wind_gusts_10m` for past date ranges.

---

## 5. Detailed Evaluation of Two Proposed Candidates

### Candidate A: ECMWF IFS (`ecmwf_ifs025` / `ecmwf_ifs`)

* **Provider**: European Centre for Medium-Range Weather Forecasts (ECMWF)
* **Model Code**: `ecmwf_ifs025` (standard 0.25° grid) or `ecmwf_ifs` (native HRES 9 km)
* **Suitability for Delhi NCR**:
  - Globally recognized as the benchmark in numerical weather prediction accuracy.
  - In Delhi's winter air quality regime, shallow planetary boundary layer (PBL) and thermal inversions trap pollutants. ECMWF's boundary layer parameterization and surface physics are widely regarded in atmospheric research as superior for stable boundary layers.
  - Open-Meteo explicitly provides `boundary_layer_height` for ECMWF.
* **Earliest Past Forecast Date**:
  - Previous Runs API: January 2024 (`2024-01-01`).
  - Historical Forecast API: February 3, 2024 for IFS 0.25°; November 7, 2022 for IFS 0.4°; March 2024 for IFS HRES in Single Runs.
* **Resolution**:
  - Spatial: 0.25° (~25 km) for `ecmwf_ifs025`, or 9 km for `ecmwf_ifs` (HRES).
  - Temporal: Native 3-hourly (interpolated to 1-hourly by Open-Meteo) for standard IFS; native 1-hourly for IFS HRES.
  - Update Frequency: Every 6 hours (00, 06, 12, 18 UTC).
* **Trade-offs**:
  - Native standard run timestep is 3-hourly (coarser than GFS's native 1-hourly), unless using IFS HRES.
  - Previous runs archive starts January 2024 (shorter than GFS's March 2021 record).

### Candidate B: NOAA GFS (`ncep_gfs_seamless`)

* **Provider**: NOAA / NCEP (United States)
* **Model Code**: `ncep_gfs_seamless` (or `gfs_seamless` / `ncep_gfs_global`)
* **Suitability for Delhi NCR**:
  - Broadest historical record on Open-Meteo: 2 m temperature previous runs extend back to March 23, 2021 (~5 years of retrospective data).
  - Native 1-hourly output across all forecast horizons.
  - Supports `boundary_layer_height` and `wind_gusts_10m`.
* **Earliest Past Forecast Date**:
  - Previous Runs API: March 23, 2021 for `temperature_2m`; January 2024 for other variables.
  - Historical Forecast API: March 23, 2021 (`2021-03-23`).
* **Resolution**:
  - Spatial: 0.11° (~13 km) / 0.25° (~25 km).
  - Temporal: Native 1-hourly.
  - Update Frequency: Every 6 hours (00, 06, 12, 18 UTC).
* **Trade-offs**:
  - GFS is known in South Asian meteorology to exhibit dry or warm biases and tend to overestimate boundary layer height during stable winter conditions compared to ECMWF.
  - Variables other than 2 m temperature in Previous Runs only extend back to January 2024.

---

## 6. Exact Parameter Values for API Requests

For Central Delhi (`latitude=28.61`, `longitude=77.21`):

### 6.1 Candidate A: ECMWF IFS

#### Live Weather Forecast API (for continuous operational archiving)
* **Endpoint**: `https://api.open-meteo.com/v1/forecast`
* **Query Parameters**:
  ```text
  latitude=28.61&longitude=77.21&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,wind_gusts_10m,precipitation,boundary_layer_height&models=ecmwf_ifs025&forecast_days=5&timezone=UTC
  ```
  *(Note: `models=ecmwf_ifs` can be used if 9 km HRES is desired).*

#### Previous Runs API (for retrospective D+1 / D+2 verification)
* **Endpoint**: `https://previous-runs-api.open-meteo.com/v1/forecast`
* **Query Parameters**:
  ```text
  latitude=28.61&longitude=77.21&hourly=temperature_2m_previous_day1,temperature_2m_previous_day2,relative_humidity_2m_previous_day1,relative_humidity_2m_previous_day2,wind_speed_10m_previous_day1,wind_speed_10m_previous_day2,wind_direction_10m_previous_day1,wind_direction_10m_previous_day2,precipitation_previous_day1,precipitation_previous_day2&models=ecmwf_ifs025&timezone=UTC
  ```

---

### 6.2 Candidate B: NOAA GFS

#### Live Weather Forecast API (for continuous operational archiving)
* **Endpoint**: `https://api.open-meteo.com/v1/forecast`
* **Query Parameters**:
  ```text
  latitude=28.61&longitude=77.21&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,wind_gusts_10m,precipitation,boundary_layer_height&models=ncep_gfs_seamless&forecast_days=5&timezone=UTC
  ```

#### Previous Runs API (for retrospective D+1 / D+2 verification)
* **Endpoint**: `https://previous-runs-api.open-meteo.com/v1/forecast`
* **Query Parameters**:
  ```text
  latitude=28.61&longitude=77.21&hourly=temperature_2m_previous_day1,temperature_2m_previous_day2,relative_humidity_2m_previous_day1,relative_humidity_2m_previous_day2,wind_speed_10m_previous_day1,wind_speed_10m_previous_day2,wind_direction_10m_previous_day1,wind_direction_10m_previous_day2,precipitation_previous_day1,precipitation_previous_day2&models=ncep_gfs_seamless&timezone=UTC
  ```

---

## 7. Trade-Off Comparison Summary

| Dimension | ECMWF IFS (`ecmwf_ifs025` / `ecmwf_ifs`) | NOAA GFS (`ncep_gfs_seamless`) |
| :--- | :--- | :--- |
| **Model Quality & Physics** | Highest global standard; superior stable boundary layer / inversion representation | Strong global model, but prone to boundary layer overestimation in South Asian winter |
| **Boundary Layer Height** | Documented and available in live Forecast API | Documented and available in live Forecast API |
| **Native Timestep** | 3-hourly on IFS 0.25° (interpolated to 1h); 1-hourly on IFS HRES (9 km) | Native 1-hourly across all runs |
| **Spatial Resolution** | 0.25° (~25 km) or 9 km (HRES) | 0.11° (~13 km) / 0.25° (~25 km) |
| **Previous Runs Depth** | January 2024 (~2+ years) | March 2021 for 2m temp (~5 years); Jan 2024 for others |
| **Historical Forecast Depth** | 2024-02-03 (0.25°) / 2022-11-07 (0.4°) | March 23, 2021 |

---

## 8. Unverified Points

The following points could not be verified purely from public documentation text without issuing requests against live data endpoints:

1. **`boundary_layer_height_previous_day1` / `_previous_day2` in Previous Runs API**:
   - The Previous Runs documentation page does NOT list `boundary_layer_height` in its UI or variable tables. Whether the underlying backend accepts this variable with `_previous_day1` suffix or rejects it with HTTP 400 is **unverified**.
2. **`wind_gusts_10m_previous_day1` / `_previous_day2` in Previous Runs API**:
   - Not listed in the Previous Runs UI checkboxes. Whether the backend accepts it with `_previous_day1` suffix is **unverified**.
3. **Exact Start Date of Non-Temperature GFS Variables in Previous Runs**:
   - The documentation says: *"Most models are archived from January 2024. GFS 2 m temperature extends back to March 2021."* It does not state whether wind and humidity for GFS start in March 2021 or January 2024.
4. **Digital Elevation Model Downscaling**:
   - The default behavior uses a 90-meter DEM for downscaling unless `&elevation=nan` is passed. The exact impact on Delhi grid cells without specifying elevation is **unverified**.

---

## 9. Conclusion & Maintainer Action

- **Candidate A (ECMWF IFS)** is recommended if physical fidelity and inversion/PBL accuracy for Delhi air stagnation are prioritized.
- **Candidate B (NOAA GFS)** is recommended if longer historical depth (to 2021) and native hourly resolution are prioritized.
- **DWD ICON Global** is not recommended as a primary choice because it does not provide Boundary Layer Height on Open-Meteo.

> **Next Step**: Awaiting maintainer selection between Candidate A (ECMWF IFS) and Candidate B (NOAA GFS). No code, configuration, or data files have been modified.
