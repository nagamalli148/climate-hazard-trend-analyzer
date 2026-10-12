from datetime import date, timedelta

from fastapi.testclient import TestClient

import main


def _records(start, temperatures, precipitation):
    records = []
    for offset, (temperature, rainfall) in enumerate(
        zip(temperatures, precipitation)
    ):
        current = date.fromisoformat(start) + timedelta(days=offset)
        records.append({
            "date": current.isoformat(),
            "max_temperature": temperature,
            "precipitation_mm": rainfall,
        })
    return records


def test_analyze_defaults_to_heatwave(monkeypatch):
    async def fake_fetch(latitude, longitude, start_date, end_date):
        if start_date == main.BASELINE_START:
            return _records(
                "1991-01-01",
                [20, 20, 20, 40],
                [0, 1, 2, 3],
            )
        return _records(
            "2020-01-01",
            [40, 41, 42],
            [0, 0, 0],
        )

    monkeypatch.setattr(main, "fetch_historical_weather", fake_fetch)

    response = TestClient(main.app).get(
        "/api/analyze?start_year=2020&end_year=2020"
    )

    assert response.status_code == 200
    result = response.json()
    assert result["hazard"] == "heatwave"
    assert result["total_events"] == 1
    assert result["yearly_data"][0]["heatwave_days"] == 3
    assert result["events"][0]["average_value"] == 41


def test_analyze_heavy_rainfall_uses_precipitation_threshold(monkeypatch):
    async def fake_fetch(latitude, longitude, start_date, end_date):
        if start_date == main.BASELINE_START:
            return _records(
                "1991-01-01",
                [20] * 5,
                [0, 1, 2, 3, 4],
            )
        return _records(
            "2020-01-01",
            [20, 20, 20],
            [4, 5, 0],
        )

    monkeypatch.setattr(main, "fetch_historical_weather", fake_fetch)

    response = TestClient(main.app).get(
        "/api/analyze?start_year=2020&end_year=2020&hazard=heavy_rainfall"
    )

    assert response.status_code == 200
    result = response.json()
    assert result["threshold_value"] == 3.8
    assert result["total_events"] == 1
    assert result["events"][0]["duration_days"] == 2
    assert result["yearly_data"][0]["hazard_days"] == 2


def test_analyze_drought_warms_up_rolling_window(monkeypatch):
    baseline = _records(
        "1991-01-01",
        [20] * 30,
        [1] * 30,
    )
    analysis = _records(
        "2019-12-03",
        [20] * 59,
        [0] * 59,
    )

    async def fake_fetch(latitude, longitude, start_date, end_date):
        return baseline if start_date == main.BASELINE_START else analysis

    monkeypatch.setattr(main, "fetch_historical_weather", fake_fetch)

    response = TestClient(main.app).get(
        "/api/analyze?start_year=2020&end_year=2020&hazard=drought"
    )

    assert response.status_code == 200
    result = response.json()
    assert result["threshold_value"] == 30
    assert result["events"][0]["start_date"] == "2020-01-01"
    assert result["events"][0]["duration_days"] == 30
