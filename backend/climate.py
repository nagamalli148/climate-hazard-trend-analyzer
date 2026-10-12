
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
