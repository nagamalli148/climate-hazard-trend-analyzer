
from climate import calculate_threshold, detect_heatwaves


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
