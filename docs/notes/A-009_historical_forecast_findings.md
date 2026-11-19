# A-009: Open-Meteo Historical Forecast & CAMS Air Quality Research Findings

**Task**: A-009 (Research only)  
**Date**: 2026-11-20  
**Status**: Completed from official Open-Meteo documentation. No data endpoint requests were executed.

---

## 1. Executive Summary & Core Questions

### (a) Are past forecast issuances available for Weather?
**Yes.** Open-Meteo provides past weather forecast issuances across three distinct APIs depending on the use case:
1. **Single Runs API** (`https://single-runs-api.open-meteo.com/v1/forecast`): Preserves the full, unstitched forecast horizon of individual model runs queryable by UTC initialisation time (`&run=YYYY-MM-DDTHH:MM`).
2. **Previous Runs API** (`https://previous-runs-api.open-meteo.com/v1/forecast`): Exposes historical forecast values aligned to fixed lead-time offsets (Day 1 to Day 7 ahead, e.g., `_previous_day1`, `_previous_day2`).
3. **Historical Forecast API** (`https://historical-forecast-api.open-meteo.com/v1/forecast`): Stitches the initial hours of successive model runs into a continuous hourly timeseries.

### (b) Are past forecast issuances available for CAMS Air Quality for India?
**No for true past forecast issuances (lead-time offsets or single runs).**
- There is **no Single Runs API** and **no Previous Runs API** for air quality.
- The standard Air Quality API (`https://air-quality-api.open-meteo.com/v1/air-quality`) permits retrieving past data via `past_days` (up to 92 days) or `start_date`/`end_date` back to August 2022 for the global CAMS domain (`cams_global`).
- However, this is served as a single stitched continuous timeline. You **cannot** query what CAMS predicted 24 hours (D+1) or 48 hours (D+2) in advance for a given target day.
- **Implication for NCR Hawa**: Our daily forecast archiving job (Task A-005) is mandatory to create a true, leakage-free historical evaluation set of D+1 and D+2 CAMS forecasts.

---

## 2. API Endpoints & Capabilities Summary

| API Name | Endpoint URL | Documentation URL | Primary Purpose | Earliest Available Date |
|---|---|---|---|---|
| **Single Runs API** | `https://single-runs-api.open-meteo.com/v1/forecast` | `https://open-meteo.com/en/docs/single-runs-api` | Individual operational model runs queryable by initialisation time (`&run=`) | ECMWF IFS: **2024-03-14**; Others: **2026-04-02** |
| **Previous Runs API** | `https://previous-runs-api.open-meteo.com/v1/forecast` | `https://open-meteo.com/en/docs/previous-runs-api` | Fixed lead-time forecasts (1–7 days before valid time: `_previous_day1` to `_previous_day7`) | GFS: **2021-03-23**; JMA: **2018**; Most models: **January 2024** |
| **Historical Forecast API** | `https://historical-forecast-api.open-meteo.com/v1/forecast` | `https://open-meteo.com/en/docs/historical-forecast-api` | Stitched continuous timeseries of first hours from successive runs | ECMWF IFS HRES: **2017-01-01**; GFS: **2021-03-23**; ICON/GEM: **November 2022** |
| **Historical Weather API** | `https://archive-api.open-meteo.com/v1/archive` | `https://open-meteo.com/en/docs/historical-weather-api` | Reanalysis data (ERA5, ERA5-Land, IFS analysis) | ERA5: **1940-01-01**; ERA5-Land: **1950-01-01** |
| **Air Quality API** | `https://air-quality-api.open-meteo.com/v1/air-quality` | `https://open-meteo.com/en/docs/air-quality-api` | Current forecast & continuous past air quality timeseries | CAMS Global (India): **August 2022**; Europe Reanalysis: **2013** |

---

## 3. Detailed Findings by Research Question

### 3.1 Weather Past Forecasts

#### Endpoints & Mechanism
- **Single Runs API Endpoint**: `https://single-runs-api.open-meteo.com/v1/forecast`
  > *Quote (`https://open-meteo.com/en/docs/single-runs-api`):*  
  > "Retrieve the full forecast horizon of any individual model run using the &run= parameter (e.g. &run=2025-09-01T00:00). Most models are archived from 2nd of April 2026. ECMWF IFS HRES at 9 km is available from March 2024."  
  > "The API endpoint https://single-runs-api.open-meteo.com/v1/forecast accepts the same parameters as the Weather Forecast API, with one additional required parameter: run."

- **Previous Runs API Endpoint**: `https://previous-runs-api.open-meteo.com/v1/forecast`
  > *Quote (`https://open-meteo.com/en/docs/previous-runs-api`):*  
  > "Data from past model runs is aligned to fixed lead-time offsets of 1–7 days. Requesting temperature_2m_previous_day1 returns the value predicted 24 hours before valid time; _previous_day2 returns 48 hours before, and so on up to day 7."  
  > "_previous_day0 is the current model run (equivalent to the live Forecast API). _previous_day1 is the value that was predicted 24 hours before valid time, _previous_day2 48 hours before, and so on up to day 7."

- **Historical Forecast API Endpoint**: `https://historical-forecast-api.open-meteo.com/v1/forecast`
  > *Quote (`https://open-meteo.com/en/docs/historical-forecast-api`):*  
  > "Historical forecasts archived from the Weather Forecast API — same models, same parameters, same response format. Coverage starts around 2022. Each run's first few hours are stitched into a continuous hourly timeseries. To access the full forecast horizon of individual runs, use the Single Runs API."

#### Models Covering India
The following global models cover India (coordinates 28°N, 77°E):
- **ECMWF IFS HRES**: 9 km resolution (IFS Cycle 49R1 / 50R1). Available from 2024-03-14 in Single Runs; 2017-01-01 in Historical Forecast.
- **ECMWF IFS 0.25° / 0.4°**: 3-hourly, updated every 6 hours. Available from 2022-11-07 (0.4°) and 2024-02-03 (0.25°).
- **NOAA GFS Global**: 0.11° (~13 km) / 0.25° (~25 km). Available from 2021-03-23.
- **DWD ICON Global**: 0.1° (~11 km). Available from 2022-11-24.
- **JMA GSM**: 0.5° (~55 km). Available from 2016-01-01.
- **GEM Global**: 0.15° (~15 km). Available from 2022-11-23.
- **CMA GFS GRAPES Global**: 0.125° (~15 km). Available from 2023-12-31.
- Default `Best match` combines the optimal models for the requested coordinates.

#### Is it a True Past Forecast or a Reanalysis?
- **Single Runs API**: **True past forecast**. Keeps the exact output of individual model runs as issued.
- **Previous Runs API**: **True past forecast**. Preserves predictions at fixed lead-time horizons (1 to 7 days ahead).
- **Historical Forecast API**: **Stitched nowcast/forecast**. Combines the initial hours of consecutive operational runs into a seamless series; reflects updated initialisations rather than a fixed lead-time forecast.
- **Historical Weather API**: **Reanalysis** (ERA5 / ERA5-Land).

---

### 3.2 Air Quality & CAMS for India

#### Endpoint & Data Availability
- **API Endpoint**: `https://air-quality-api.open-meteo.com/v1/air-quality`
- **Global Model**: `CAMS Global Atmospheric Composition Forecasts`
  > *Quote (`https://open-meteo.com/en/docs/air-quality-api`):*  
  > "Data Set: CAMS Global Atmospheric Composition Forecasts | Region: Global 🌍 | Spatial Resolution: 0.4° (~45 km) | Temporal Resolution: 3-Hourly | Forecast Length: 5 days | Data Availability: August 2022 onwards | Update frequency: Every 12 hours"

- **European Datasets (Europe Only)**:
  > *Quote (`https://open-meteo.com/en/docs/air-quality-api`):*  
  > "CAMS European Air Quality Forecast | Region: Europe | Spatial Resolution: 0.1° (~11 km) | Temporal Resolution: Hourly | Forecast Length: 4 days | Data Availability: October 2023 onwards | Update frequency: Every 24 hours"  
  > "CAMS European Air Quality Reanalysis | Region: Europe | Spatial Resolution: 0.1° (~11 km) | Temporal Resolution: Hourly | Forecast Length: - | Data Availability: 2013 onwards"

- **Greenhouse Gas Global Model**:
  > *Quote (`https://open-meteo.com/en/docs/air-quality-api`):*  
  > "CAMS Global Greenhouse Gas Forecast | Region: Global 🌍 | Spatial Resolution: 0.1° (~11 km) | Temporal Resolution: 3-Hourly | Forecast Length: 5 days | Data Availability: November 2024 onwards | Update frequency: Every 24 hours"

#### PM2.5 Variables for India
For Delhi-NCR (India), the domain must be global (`domains=cams_global` or `auto`). The available PM2.5-related variables are:
- `pm2_5`:
  > *Quote (`https://open-meteo.com/en/docs/air-quality-api`):*  
  > "pm2_5 | Instant | μg/m³ | Particulate matter with diameter smaller than 10 µm (PM10) and smaller than 2.5 µm (PM2.5) close to surface (10 meter above ground)"
- `us_aqi_pm2_5`:
  > *Quote (`https://open-meteo.com/en/docs/air-quality-api`):*  
  > "United States Air Quality Index (AQI) calculated for different particulate matter and gases individually... us_aqi_pm2_5"
- `european_aqi_pm2_5`:
  > *Quote (`https://open-meteo.com/en/docs/air-quality-api`):*  
  > "European Air Quality Index (AQI) calculated for different particulate matter and gases individually... european_aqi_pm2_5"

*(Note: Variables marked `(*)` like `pm2_5_total_organic_matter` or pollen types are documented as "Only available for Europe" / "CAMS European Air Quality forecast".)*

#### Is CAMS Data for India a True Past Forecast or Reanalysis?
- Open-Meteo provides an explicit **reanalysis** only for Europe (`CAMS European Air Quality Reanalysis` from 2013).
- For India / Global, Open-Meteo provides only `CAMS Global Atmospheric Composition Forecasts` from **August 2022 onwards**.
- Historical requests (`past_days` or `start_date`/`end_date`) return data from an operational stitched archive.
- Open-Meteo **does not provide** a Previous Runs or Single Runs API for CAMS air quality. Past forecast issuances at fixed lead times (e.g. what CAMS predicted for Delhi 24h or 48h before the target hour) **cannot be queried**.

---

### 3.3 Usage Terms, Licences & Limits

#### Non-Commercial Use Definition & Scope
> *Quote (`https://open-meteo.com/en/terms`):*  
> "You may only use the free API services for non-commercial purposes."  
> "Private or non-profit websites or apps that do not have subscriptions or advertising. Personal home automation purposes. Public research conducted at public institutions. Use in educational content."  
> "On the other hand, the following examples are considered commercial use: Websites or apps that have subscriptions or display advertisements. Commercial products or promotional activities. Undisclosed research at commercial entities."

#### Rate Limits (Free Tier)
> *Quote (`https://open-meteo.com/en/terms` & `https://open-meteo.com/en/pricing`):*  
> - Minutely Limit: **600 calls / min**  
> - Hourly Limit: **5,000 calls / hour**  
> - Daily Limit: **10,000 calls / day**  
> - Monthly Limit: **300,000 calls / month**  
> *(Note on pricing page: "A usage statistics portal is under development. Until it is available, monthly limits are not enforced.")*

#### Licence & Attribution Requirements
> *Quote (`https://open-meteo.com/en/licence`):*  
> "API data are offered under Attribution 4.0 International (CC BY 4.0)"  
> "You must include a link next to any location Open-Meteo data are displayed, for example: `<a href=\"https://open-meteo.com/\">Weather data by Open-Meteo.com</a>`"

> *Quote (`https://open-meteo.com/en/docs/air-quality-api`):*  
> "All users of Open-Meteo data must provide a clear attribution to CAMS ENSEMBLE data provider as well as a reference to Open-Meteo."

---

## 4. List of Unverified Points

The following points could not be verified directly from the fetched documentation text:

1. **Exact Run Stitching Logic for Past Air Quality**:
   - The documentation states that historical air quality data is available from August 2022, but does not document how successive 12-hourly forecast runs (00 and 12 UTC) are spliced into a continuous past series (e.g., whether hours 0–11 of each run are retained, or if later analysis cycles overwrite earlier hours).
2. **Exact Starting Day of Global CAMS Archive in August 2022**:
   - The documentation table states "August 2022 onwards", but does not specify the precise calendar date (e.g., 2022-08-01 vs late August).
3. **Future Single-Run Archival for CAMS Air Quality**:
   - The documentation does not state whether Single Runs or lead-time offsets (`_previous_dayN`) will ever be supported for CAMS air quality, or if it is restricted permanently to weather models due to storage constraints.
4. **Enforcement Timeline for the Monthly 300,000 Call Limit**:
   - The pricing page notes that monthly limits are not currently enforced while the statistics portal is in development, but gives no scheduled date for when enforcement begins.
