
from climate import (
    calculate_rolling_precipitation,
    calculate_threshold,
    detect_droughts,
    detect_heavy_rainfall,
    detect_heatwaves,
)


def test_calculate_threshold():
    temperatures = [10, 20, 30, 40, 50]

    threshold = calculate_threshold(
        temperatures,
        percentile=50,
    )

    assert threshold == 30


def test_detect_heatwaves():
    records = [
        {"date": "2020-04-01", "max_temperature": 39},
        {"date": "2020-04-02", "max_temperature": 40},
        {"date": "2020-04-03", "max_temperature": 39},
        {"date": "2020-04-04", "max_temperature": 35},
        {"date": "2020-04-05", "max_temperature": 39},
        {"date": "2020-04-06", "max_temperature": 41},
        {"date": "2020-04-07", "max_temperature": 42},
        {"date": "2020-04-08", "max_temperature": 43},
    ]

    events = detect_heatwaves(
        records,
        threshold=38,
        min_duration=3,
    )

    assert len(events) == 2

    assert events[0]["start_date"] == "2020-04-01"
    assert events[0]["end_date"] == "2020-04-03"
    assert events[0]["duration_days"] == 3

    assert events[1]["start_date"] == "2020-04-05"
    assert events[1]["end_date"] == "2020-04-08"
    assert events[1]["duration_days"] == 4


def test_missing_temperature_breaks_event():
    records = [
        {"date": "2020-04-01", "max_temperature": 39},
        {"date": "2020-04-02", "max_temperature": 40},
        {"date": "2020-04-03", "max_temperature": None},
        {"date": "2020-04-04", "max_temperature": 41},
        {"date": "2020-04-05", "max_temperature": 42},
    ]

    events = detect_heatwaves(records, threshold=38)

    assert events == []


def test_detect_heavy_rainfall_groups_consecutive_days():
    records = [
        {"date": "2020-01-01", "precipitation_mm": 11},
        {"date": "2020-01-02", "precipitation_mm": 12},
        {"date": "2020-01-03", "precipitation_mm": 10},
        {"date": "2020-01-04", "precipitation_mm": 20},
        {"date": "2020-01-05", "precipitation_mm": None},
        {"date": "2020-01-06", "precipitation_mm": 15},
    ]

    events = detect_heavy_rainfall(records, threshold=10)

    assert len(events) == 3
    assert events[0]["start_date"] == "2020-01-01"
    assert events[0]["end_date"] == "2020-01-02"
    assert events[0]["total_precipitation_mm"] == 23
    assert events[1]["duration_days"] == 1
    assert events[2]["start_date"] == "2020-01-06"


def test_rolling_precipitation_does_not_bridge_missing_calendar_days():
    records = [
        {"date": "2020-01-01", "precipitation_mm": 1},
        {"date": "2020-01-02", "precipitation_mm": 2},
        {"date": "2020-01-04", "precipitation_mm": 3},
        {"date": "2020-01-05", "precipitation_mm": 4},
    ]

    totals = calculate_rolling_precipitation(records, window_days=2)

    assert totals == [
        {"date": "2020-01-02", "precipitation_mm": 3},
        {"date": "2020-01-05", "precipitation_mm": 7},
    ]


def test_detect_droughts_includes_threshold_and_respects_analysis_period():
    records = [
        {"date": "2020-01-01", "precipitation_mm": 1},
        {"date": "2020-01-02", "precipitation_mm": 1},
        {"date": "2020-01-03", "precipitation_mm": 1},
        {"date": "2020-01-04", "precipitation_mm": 1},
        {"date": "2020-01-05", "precipitation_mm": 20},
        {"date": "2020-01-06", "precipitation_mm": 30},
    ]

    events = detect_droughts(
        records,
        threshold=2,
        min_duration=3,
        window_days=2,
        start_date="2020-01-02",
        end_date="2020-01-06",
    )

    assert len(events) == 1
    assert events[0]["start_date"] == "2020-01-02"
    assert events[0]["end_date"] == "2020-01-04"
    assert events[0]["duration_days"] == 3
