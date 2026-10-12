
from datetime import date, timedelta
from math import ceil


def calculate_threshold(temperatures, percentile=95):
    """Calculate a percentile threshold from valid temperatures."""
    valid = sorted(
        float(temp)
        for temp in temperatures
        if temp is not None
    )

    if not valid:
        raise ValueError("No valid temperatures available")

    if not 0 <= percentile <= 100:
        raise ValueError("Percentile must be between 0 and 100")

    # Linear interpolation between neighboring values.
    position = (len(valid) - 1) * percentile / 100
    lower = int(position)
    upper = ceil(position)

    if lower == upper:
        return valid[lower]

    fraction = position - lower

    return (
        valid[lower] * (1 - fraction)
        + valid[upper] * fraction
    )


def calculate_rolling_precipitation(records, window_days=30):
    """Return full-window precipitation totals, resetting across gaps."""
    if window_days < 1:
        raise ValueError("Window must contain at least one day")

    ordered = sorted(records, key=lambda record: record["date"])
    window = []
    rolling_totals = []
    previous_date = None

    for record in ordered:
        current_date = date.fromisoformat(record["date"])
        precipitation = record.get("precipitation_mm")

        if (
            previous_date is not None
            and current_date != previous_date + timedelta(days=1)
        ):
            window.clear()

        if precipitation is None:
            window.clear()
        else:
            window.append(float(precipitation))
            if len(window) > window_days:
                window.pop(0)

            if len(window) == window_days:
                rolling_totals.append({
                    "date": current_date.isoformat(),
                    "precipitation_mm": sum(window),
                })

        previous_date = current_date

    return rolling_totals


def detect_heavy_rainfall(records, threshold, min_duration=1):
    """Group consecutive days above the precipitation threshold into events."""
    if min_duration < 1:
        raise ValueError("Minimum duration must be at least 1")

    ordered = sorted(records, key=lambda record: record["date"])
    events = []
    current_event = []

    def save_event():
        if len(current_event) >= min_duration:
            precipitation = [
                record["precipitation_mm"]
                for record in current_event
            ]
            events.append({
                "start_date": current_event[0]["date"],
                "end_date": current_event[-1]["date"],
                "duration_days": len(current_event),
                "average_precipitation_mm": round(
                    sum(precipitation) / len(precipitation), 2
                ),
                "max_precipitation_mm": max(precipitation),
                "total_precipitation_mm": round(sum(precipitation), 2),
            })

        current_event.clear()

    previous_date = None

    for record in ordered:
        current_date = date.fromisoformat(record["date"])
        precipitation = record.get("precipitation_mm")

        if (
            previous_date is not None
            and current_date != previous_date + timedelta(days=1)
        ):
            save_event()

        if precipitation is None or precipitation <= threshold:
            save_event()
        else:
            current_event.append({
                "date": current_date.isoformat(),
                "precipitation_mm": float(precipitation),
            })

        previous_date = current_date

    save_event()
    return events


def detect_droughts(
    records,
    threshold,
    min_duration=30,
    window_days=30,
    start_date=None,
    end_date=None,
):
    """
    Find runs of days with rolling precipitation below the baseline threshold.

    The records may include pre-period days to warm up the first rolling window;
    only rolling totals ending inside the requested analysis period are counted.
    """
    if min_duration < 1:
        raise ValueError("Minimum duration must be at least 1")

    analysis_start = (
        date.fromisoformat(start_date) if start_date is not None else None
    )
    analysis_end = (
        date.fromisoformat(end_date) if end_date is not None else None
    )

    rolling_totals = calculate_rolling_precipitation(
        records,
        window_days=window_days,
    )
    events = []
    current_event = []

    def save_event():
        if len(current_event) >= min_duration:
            amounts = [
                record["precipitation_mm"]
                for record in current_event
            ]
            events.append({
                "start_date": current_event[0]["date"],
                "end_date": current_event[-1]["date"],
                "duration_days": len(current_event),
                "average_30_day_precipitation_mm": round(
                    sum(amounts) / len(amounts), 2
                ),
                "minimum_30_day_precipitation_mm": round(min(amounts), 2),
            })

        current_event.clear()

    previous_date = None

    for record in rolling_totals:
        current_date = date.fromisoformat(record["date"])

        if (
            previous_date is not None
            and current_date != previous_date + timedelta(days=1)
        ):
            save_event()

        outside_period = (
            (analysis_start is not None and current_date < analysis_start)
            or (analysis_end is not None and current_date > analysis_end)
        )

        if outside_period or record["precipitation_mm"] > threshold:
            save_event()
        else:
            current_event.append(record)

        previous_date = current_date

    save_event()
    return events


def detect_heatwaves(records, threshold, min_duration=3):
    """
    Find consecutive heatwave days.

    A day qualifies when its maximum temperature is strictly
    greater than the threshold.

    Missing temperatures or missing calendar dates break a sequence.
    """
    if min_duration < 1:
        raise ValueError("Minimum duration must be at least 1")

    # Sort records chronologically.
    ordered = sorted(
        records,
        key=lambda record: record["date"]
    )

    events = []
    current_event = []

    def save_event():
        if len(current_event) >= min_duration:
            temperatures = [
                record["max_temperature"]
                for record in current_event
            ]

            events.append({
                "start_date": current_event[0]["date"].isoformat(),
                "end_date": current_event[-1]["date"].isoformat(),
                "duration_days": len(current_event),
                "average_temperature": round(
                    sum(temperatures) / len(temperatures), 2
                ),
                "max_temperature": max(temperatures),
            })

        current_event.clear()

    previous_date = None

    for record in ordered:
        current_date = date.fromisoformat(record["date"])
        temperature = record["max_temperature"]

        # A missing date breaks the consecutive-day sequence.
        if (
            previous_date is not None
            and current_date != previous_date + timedelta(days=1)
        ):
            save_event()

        # Missing temperature: do not infer a heatwave.
        if temperature is None:
            save_event()
        elif temperature > threshold:
            current_event.append({
                "date": current_date,
                "max_temperature": float(temperature),
            })
        else:
            save_event()

        previous_date = current_date

    save_event()

    return events
