# NCR Hawa: Delhi-NCR Air Quality Forecast

Forecasts the air quality category for Delhi-NCR for the next 24 and 48 hours, compared honestly against simple baselines.

[Live web page] | [Download APK] | [Play Store link if live]

> NCR Hawa is an independent app by an individual developer. It is **not** an official government service and is not connected to, endorsed by, or operated by any government body or air-monitoring agency. Forecasts are statistical estimates and can be wrong. The health notes are general information and **not medical advice**; if you feel unwell or have a medical condition, speak to a doctor. For official air-quality information, visit the relevant government sources.
> The category shown is based on PM2.5 and may differ from the official Air Quality Index, which considers multiple pollutants.

## Problem and users
Delhi-NCR residents need understandable, forward-looking 24-h and 48-h air quality forecasts to plan school runs, outdoor activities, and daily commutes. Existing public tools primarily report historical or real-time conditions rather than verified local forecasts.

## What it does
- Collects public air quality observations and weather/CAMS forecasts.
- Predicts PM2.5 levels and derived categories for D+1 and D+2 horizons.
- Explicitly presents baseline forecasts (persistence, climatology, raw CAMS) alongside model predictions.
- Delivers static JSON consumed by a public web page and an Android application.

## How accurate is it?
All performance metrics are evaluated on frozen test seasons and prospective daily monitoring.

| Horizon | Model MAE | Persistence MAE | CAMS MAE | Poor+ recall (model / persistence) |
|---|---|---|---|---|
| D+1 | not measured | not measured | not measured | not measured |
| D+2 | not measured | not measured | not measured | not measured |

Result on frozen test season: not measured. Live since: not measured.

If the model does not beat a baseline, it is stated here explicitly.

## Data sources and licences
- **OpenAQ v3 API**: Ground station observations (licences vary by reporting station).
- **Open-Meteo Air Quality API**: CAMS global atmospheric model forecast (CC BY 4.0; non-commercial).
- **Open-Meteo Weather Forecast API**: Numerical weather prediction (CC BY 4.0; non-commercial).
- **NASA FIRMS** (optional): Active fire hotspot detections.

## Architecture and how to run
System design: Public data ingest -> Raw archive -> Feature building -> Model/baselines -> Static JSON generation -> Web & Android clients.

### Local setup
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.lock
ruff check .
pytest
```

## MLOps: what is automated, what is not
- Automated: Scheduled observation/forecast ingest, daily verification against actuals, static JSON export, CI linting and tests.
- Manual: Model promotion gates, data licence auditing, Play Store releases.

## Limitations
- Coarse 0.4° (~45 km) CAMS global forecast grid.
- PM2.5-based category classification may differ from multi-pollutant national AQI.
- Ground station sensor outages, data revision lag, and episodic events (Diwali, crop residue burning).

## Privacy and safety
No user accounts, no advertisements, and no user tracking or personal data collection.
See [AQ_16_Legal_and_Privacy_Pack.md](docs/AQ_16_Legal_and_Privacy_Pack.md) for full terms and policies.

## AI assistance
Built with an AI coding agent under human supervision. Modelling and evaluation designed and verified by maintainer. See `docs/AQ_17_Admin_Templates.md` (AI Assistance Log).

## Licence and third-party notices
Source code is released under the MIT Licence. Third-party data terms and attributions are maintained in project documentation.
