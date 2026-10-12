
from datetime import date, timedelta
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from database import check_database
from weather import fetch_historical_weather

from climate import (
    calculate_rolling_precipitation,
    calculate_threshold,
    detect_droughts,
    detect_heavy_rainfall,
    detect_heatwaves,
)

BASELINE_START = "1991-01-01"
BASELINE_END = "2020-12-31"
PRECIPITATION_WINDOW_DAYS = 30
HAZARD_CONFIG = {
    "heatwave": {
        "title": "Heatwave",
        "threshold_percentile": 95,
        "threshold_unit": "°C",
        "value_unit": "°C",
        "day_label": "Heatwave days",
        "threshold_label": "95th-percentile temperature threshold",
        "extreme_label": "Maximum temperature",
    },
    "drought": {
        "title": "Drought",
        "threshold_percentile": 20,
        "threshold_unit": "mm / 30 days",
        "value_unit": "mm / 30 days",
        "day_label": "Drought-indicator days",
        "threshold_label": "20th-percentile 30-day rainfall threshold",
        "extreme_label": "Minimum 30-day rainfall",
    },
    "heavy_rainfall": {
        "title": "Heavy rainfall",
        "threshold_percentile": 95,
        "threshold_unit": "mm / day",
        "value_unit": "mm",
        "day_label": "Heavy-rainfall days",
        "threshold_label": "95th-percentile daily rainfall threshold",
        "extreme_label": "Maximum daily rainfall",
    },
}

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
            "precipitation_unit": "mm",
            "record_count": len(records),
            "data": records,
        }

    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail="Unable to retrieve historical weather data",
        ) from exc



@app.get("/api/analyze")
async def analyze_hazards(
    latitude: float = Query(16.5062, ge=-90, le=90),
    longitude: float = Query(80.648, ge=-180, le=180),
    start_year: int = Query(2000, ge=1940, le=2025),
    end_year: int = Query(2020, ge=1940, le=2025),
    hazard: Literal["heatwave", "drought", "heavy_rainfall"] = "heatwave",
):
    if start_year > end_year:
        raise HTTPException(
            status_code=400,
            detail="Start year must not exceed end year",
        )

    try:
        analysis_start = date(start_year, 1, 1)
        analysis_end = date(end_year, 12, 31)
        fetch_start = analysis_start

        if hazard == "drought":
            fetch_start -= timedelta(days=PRECIPITATION_WINDOW_DAYS - 1)

        # Fetch prior days to seed the first rolling drought window.
        analysis_records = await fetch_historical_weather(
            latitude,
            longitude,
            fetch_start.isoformat(),
            analysis_end.isoformat(),
        )

        baseline_records = await fetch_historical_weather(
            latitude,
            longitude,
            BASELINE_START,
            BASELINE_END,
        )

        config = HAZARD_CONFIG[hazard]
        if hazard == "heatwave":
            baseline_values = [
                record["max_temperature"]
                for record in baseline_records
                if record["max_temperature"] is not None
            ]
            threshold = calculate_threshold(
                baseline_values,
                percentile=config["threshold_percentile"],
            )
            events = detect_heatwaves(
                analysis_records,
                threshold=threshold,
                min_duration=3,
            )
            minimum_duration = 3
        elif hazard == "heavy_rainfall":
            baseline_values = [
                record["precipitation_mm"]
                for record in baseline_records
                if record["precipitation_mm"] is not None
            ]
            threshold = calculate_threshold(
                baseline_values,
                percentile=config["threshold_percentile"],
            )
            events = detect_heavy_rainfall(
                analysis_records,
                threshold=threshold,
            )
            minimum_duration = 1
        else:
            baseline_rolling_totals = calculate_rolling_precipitation(
                baseline_records,
                window_days=PRECIPITATION_WINDOW_DAYS,
            )
            baseline_values = [
                record["precipitation_mm"]
                for record in baseline_rolling_totals
            ]
            threshold = calculate_threshold(
                baseline_values,
                percentile=config["threshold_percentile"],
            )
            events = detect_droughts(
                analysis_records,
                threshold=threshold,
                min_duration=PRECIPITATION_WINDOW_DAYS,
                window_days=PRECIPITATION_WINDOW_DAYS,
                start_date=analysis_start.isoformat(),
                end_date=analysis_end.isoformat(),
            )
            minimum_duration = PRECIPITATION_WINDOW_DAYS

        yearly = {
            year: {
                "year": year,
                "event_count": 0,
                "hazard_days": 0,
                "durations": [],
            }
            for year in range(start_year, end_year + 1)
        }

        for event in events:
            event_start = date.fromisoformat(event["start_date"])
            event_end = date.fromisoformat(event["end_date"])
            yearly[event_start.year]["event_count"] += 1
            yearly[event_start.year]["durations"].append(
                event["duration_days"]
            )

            current = event_start

            while current <= event_end:
                if current.year in yearly:
                    yearly[current.year]["hazard_days"] += 1

                current += timedelta(days=1)

        yearly_data = []
        for metrics in yearly.values():
            durations = metrics.pop("durations")
            metrics["average_duration_days"] = (
                round(sum(durations) / len(durations), 2)
                if durations
                else 0
            )
            if hazard == "heatwave":
                metrics["heatwave_days"] = metrics["hazard_days"]
            yearly_data.append(metrics)

        event_values = []
        for event in events:
            if hazard == "heatwave":
                average_value = event["average_temperature"]
                extreme_value = event["max_temperature"]
            elif hazard == "heavy_rainfall":
                average_value = event["average_precipitation_mm"]
                extreme_value = event["max_precipitation_mm"]
            else:
                average_value = event["average_30_day_precipitation_mm"]
                extreme_value = event["minimum_30_day_precipitation_mm"]

            event_values.append({
                **event,
                "average_value": average_value,
                "extreme_value": extreme_value,
                "value_unit": config["value_unit"],
            })

        event_counts = [
            metrics["event_count"] for metrics in yearly_data
        ]
        event_count_slope = _linear_slope(event_counts)
        if len(event_counts) < 2:
            trend_direction = "insufficient data"
            events_per_decade = None
        else:
            trend_direction = (
                "increasing"
                if event_count_slope > 0.005
                else "decreasing"
                if event_count_slope < -0.005
                else "stable"
            )
            events_per_decade = round(event_count_slope * 10, 2)

        duration_points = [
            metrics
            for metrics in yearly_data
            if metrics["event_count"] > 0
        ]
        duration_slope = _linear_slope(
            [metrics["average_duration_days"] for metrics in duration_points],
            years=[metrics["year"] for metrics in duration_points],
        )
        if len(duration_points) < 2:
            duration_direction = "insufficient data"
            duration_days_per_decade = None
        else:
            duration_direction = (
                "increasing"
                if duration_slope > 0.005
                else "decreasing"
                if duration_slope < -0.005
                else "stable"
            )
            duration_days_per_decade = round(duration_slope * 10, 2)

        trend_parts = [f"{config['title']} frequency is {trend_direction}"]
        if events_per_decade is not None:
            trend_parts[0] += f" ({events_per_decade:+.2f} events per decade)"
        trend_parts.append(
            f"average event duration is {duration_direction}"
        )
        if duration_days_per_decade is not None:
            trend_parts[-1] += (
                f" ({duration_days_per_decade:+.2f} days per decade)"
            )
        insight = "; ".join(trend_parts) + " by linear regression."

        result = {
            "location": {
                "latitude": latitude,
                "longitude": longitude,
            },
            "hazard": hazard,
            "analysis_period": {
                "start_year": start_year,
                "end_year": end_year,
            },
            "baseline_period": "1991-2020",
            "threshold_value": round(threshold, 2),
            "threshold_unit": config["threshold_unit"],
            "threshold_percentile": config["threshold_percentile"],
            "minimum_consecutive_days": minimum_duration,
            "total_events": len(events),
            "total_hazard_days": sum(
                item["hazard_days"] for item in yearly_data
            ),
            "events": event_values,
            "yearly_data": yearly_data,
            "trend": {
                "direction": trend_direction,
                "frequency_direction": trend_direction,
                "events_per_decade": events_per_decade,
                "duration_direction": duration_direction,
                "average_duration_days_per_decade": (
                    duration_days_per_decade
                ),
                "method": "linear regression",
            },
            "insight": insight,
            "labels": {
                "hazard": config["title"],
                "days": config["day_label"],
                "threshold": config["threshold_label"],
                "extreme": config["extreme_label"],
            },
        }

        if hazard == "heatwave":
            result.update({
                "threshold_celsius": round(threshold, 2),
                "percentile": config["threshold_percentile"],
                "total_heatwave_days": result["total_hazard_days"],
            })

        return {
            **result,
            "methodology_note": _methodology_note(
                hazard,
                config,
                minimum_duration,
            ),
        }

    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail="Unable to retrieve historical weather data",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Unable to analyze the available weather data: {exc}",
        ) from exc


@app.get("/api/health/database")
async def database_health():
    connected = await check_database()

    return {
        "database": "mongodb",
        "connected": connected,
    }


def _linear_slope(values, years=None):
    """Return the least-squares slope for values indexed by year."""
    if len(values) < 2:
        return 0.0

    x_values = years if years is not None else range(len(values))
    x_mean = sum(x_values) / len(x_values)
    y_mean = sum(values) / len(values)
    numerator = sum(
        (year - x_mean) * (value - y_mean)
        for year, value in zip(x_values, values)
    )
    denominator = sum(
        (year - x_mean) ** 2
        for year in x_values
    )
    return numerator / denominator


def _methodology_note(hazard, config, minimum_duration):
    if hazard == "heatwave":
        rule = (
            "at least 3 consecutive days with maximum temperature above "
            "the local 95th-percentile threshold"
        )
    elif hazard == "heavy_rainfall":
        rule = (
            "daily precipitation above the local 95th-percentile threshold; "
            "consecutive exceedance days are grouped into one event"
        )
    else:
        rule = (
            "at least 30 consecutive days when rolling 30-day precipitation "
            "is at or below the local 20th-percentile baseline threshold"
        )

    return (
        f"Uses the 1991-2020 baseline. Detects {rule}. "
        f"The minimum event duration is {minimum_duration} day(s). "
        "These are simplified indicators, not official warning products."
    )