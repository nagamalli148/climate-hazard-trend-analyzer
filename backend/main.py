
from datetime import date
from database import check_database
import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from weather import fetch_historical_weather
from collections import defaultdict
from datetime import date, timedelta

from climate import calculate_threshold, detect_heatwaves

app = FastAPI(
    title="Climate Hazard Trend Analyzer",
    description="Analyze historical climate hazards for a selected region.",
    version="1.0.0",
)

# Allow requests from the local React development server.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


# 1. Check whether the backend is running.
@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "message": "Climate Hazard API is running",
    }


# 2. Fetch historical weather data.
@app.get("/api/weather")
async def get_weather(
    latitude: float = Query(16.5062, ge=-90, le=90),
    longitude: float = Query(80.648, ge=-180, le=180),
    start_date: date = date(2020, 1, 1),
    end_date: date = date(2020, 12, 31),
):
    if start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="Start date must not be after end date",
        )

    try:
        records = await fetch_historical_weather(
            latitude,
            longitude,
            start_date.isoformat(),
            end_date.isoformat(),
        )

        return {
            "location": {
                "latitude": latitude,
                "longitude": longitude,
            },
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "unit": "°C",
            "record_count": len(records),
            "data": records,
        }

    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail="Unable to retrieve historical weather data",
        ) from exc



@app.get("/api/analyze")
async def analyze_heatwaves(
    latitude: float = Query(16.5062, ge=-90, le=90),
    longitude: float = Query(80.648, ge=-180, le=180),
    start_year: int = Query(2000, ge=1940, le=2025),
    end_year: int = Query(2020, ge=1940, le=2025),
):
    if start_year > end_year:
        raise HTTPException(
            status_code=400,
            detail="Start year must not exceed end year",
        )

    try:
        # 1. Fetch the fixed historical baseline.
        # baseline_records = await fetch_historical_weather(
        #     latitude,
        #     longitude,
        #     "1991-01-01",
        #     "2020-12-31",
        # )

        # baseline_temperatures = [
        #     record["max_temperature"]
        #     for record in baseline_records
        #     if record["max_temperature"] is not None
        # ]

        # if not baseline_temperatures:
        #     raise HTTPException(
        #         status_code=422,
        #         detail="No valid baseline temperatures available",
        #     )

        # # 2. Calculate the 95th-percentile threshold.
        # threshold = calculate_threshold(
        #     baseline_temperatures,
        #     percentile=95,
        # )

        # 3. Fetch the requested analysis period.
        analysis_records = await fetch_historical_weather(
            latitude,
            longitude,
            f"{start_year}-01-01",
            f"{end_year}-12-31",
        )

        baseline_temperatures = [
            record["max_temperature"]
            for record in analysis_records
            if record["max_temperature"] is not None
         ]

        # 4. Detect qualifying events.
        threshold=calculate_threshold(baseline_temperatures,percentile=95)
        events = detect_heatwaves(
            analysis_records,
            threshold=threshold,
            min_duration=3,
        )

        # 5. Prepare yearly metrics.
        yearly = {
            year: {
                "year": year,
                "event_count": 0,
                "heatwave_days": 0,
                "durations": [],
            }
            for year in range(start_year, end_year + 1)
        }

        for event in events:
            event_start = date.fromisoformat(event["start_date"])
            event_end = date.fromisoformat(event["end_date"])

            # Count an event in the year it starts.
            yearly[event_start.year]["event_count"] += 1
            yearly[event_start.year]["durations"].append(
                event["duration_days"]
            )

            # Allocate heatwave days to their actual calendar years.
            current = event_start

            while current <= event_end:
                if current.year in yearly:
                    yearly[current.year]["heatwave_days"] += 1

                current += timedelta(days=1)

        # 6. Calculate average event duration for each year.
        yearly_data = []

        for year, metrics in yearly.items():
            durations = metrics.pop("durations")

            metrics["average_duration_days"] = (
                round(sum(durations) / len(durations), 2)
                if durations
                else 0
            )

            yearly_data.append(metrics)

        # 7. Return the analysis results.
        return {
            "location": {
                "latitude": latitude,
                "longitude": longitude,
            },
            "hazard": "heatwave",
            "analysis_period": {
                "start_year": start_year,
                "end_year": end_year,
            },
            "baseline_period": "1991-2020",
            "threshold_celsius": round(threshold, 2),
            "percentile": 95,
            "minimum_consecutive_days": 3,
            "total_events": len(events),
            "total_heatwave_days": sum(
                item["heatwave_days"] for item in yearly_data
            ),
            "events": events,
            "yearly_data": yearly_data,
            "methodology_note": (
                "Uses a single 95th-percentile threshold from all valid "
                "daily baseline temperatures. This is a simplified "
                "definition, not an official regional heatwave warning."
            ),
        }

    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail="Unable to retrieve historical weather data",
        ) from exc


@app.get("/api/health/database")
async def database_health():
    connected = await check_database()

    return {
        "database": "mongodb",
        "connected": connected,
    }