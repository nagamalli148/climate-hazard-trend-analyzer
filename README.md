# Climate Hazard Trend Analyzer

A React and FastAPI application for exploring historical heatwave, drought, and
heavy-rainfall indicators at a selected latitude and longitude.

## Run locally

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```

The API is available at `http://127.0.0.1:8000`. MongoDB is optional for local
analysis; without `MONGODB_URI`, requests use Open-Meteo directly and skip the
database cache. To enable caching, set `MONGODB_URI` and optionally
`MONGODB_DATABASE` in `backend/.env`.

### Frontend

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL printed in the terminal. The interface defaults to heatwave
analysis; select drought or heavy rainfall from the hazard menu. Vite proxies
`/api` requests to the local FastAPI server.

## Architecture and data

- **Frontend:** React, Vite, and Recharts. The UI sends coordinates, a year
  range, and a hazard selection to `GET /api/analyze`.
- **Backend:** FastAPI fetches daily maximum temperature and precipitation
  totals from the Open-Meteo Historical Weather API. The API validates
  coordinates and year ranges and returns event records, yearly summaries,
  thresholds, and a frequency trend.
- **Cache:** MongoDB stores daily weather records in a location/date-range
  cache. Requests first check for an exact or containing cached range. Set
  `MONGODB_URI` to enable it.

## Hazard logic and assumptions

All thresholds use a fixed 1991–2020 baseline for the selected coordinates;
analysis-year data is not used to set its own threshold. Percentiles use linear
interpolation. Missing values do not count as hazard days, and gaps in dates
break event sequences or rolling precipitation windows.

- **Heatwave:** at least 3 consecutive days with maximum temperature strictly
  above the baseline 95th percentile.
- **Heavy rainfall:** a daily precipitation total strictly above the baseline
  95th percentile. Consecutive qualifying days are grouped into one event.
- **Drought:** at least 30 consecutive days whose rolling 30-day precipitation
  total is at or below the baseline 20th percentile of 30-day totals. The
  backend fetches 29 warm-up days before the selected analysis period, so its
  first day can have a full rolling window. Reported drought days are days
  meeting this rolling-indicator rule.

The drought and heavy-rainfall thresholds are explicit project assumptions:
the case study suggests those hazards but does not specify their scientific
definitions. The indicators are simplified and are not official warning
products. Yearly event counts and average durations are assigned to the event's
start year; event days are assigned to their calendar years. The trend insight
uses least-squares linear trends in annual event counts and average event
durations, expressed per decade; it is descriptive and not a forecast.

## Tests and build

```powershell
cd backend
pytest
```

```powershell
cd frontend
npm run lint
npm run build
```

## AI tools

Copilot SDK in VS Code was used to implement the hazard-analysis changes,
review the requirements, and run focused verification. The code and analysis
assumptions should be reviewed before use as operational climate guidance.

## Improvements with more time

- Add regional selection by named place or bounding box.
- Add export of event summaries and trend charts.
- Compare additional drought indices and precipitation baselines, and validate
  the chosen definitions with climate-domain experts.
- Add API rate limiting and persist computed analysis summaries.
