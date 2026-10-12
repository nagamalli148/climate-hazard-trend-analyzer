import asyncio
from unittest.mock import AsyncMock

import weather


def test_fetch_historical_weather_requests_and_returns_both_variables(
    monkeypatch,
):
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "daily": {
                    "time": ["2020-01-01", "2020-01-02"],
                    "temperature_2m_max": [25.0, 26.0],
                    "precipitation_sum": [0.0, 4.5],
                }
            }

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

        async def get(self, url, params):
            assert params["daily"] == (
                "temperature_2m_max,precipitation_sum"
            )
            return Response()

    saved_records = AsyncMock()
    monkeypatch.setattr(
        weather,
        "get_cached_weather",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(weather, "save_cached_weather", saved_records)
    monkeypatch.setattr(
        weather.httpx,
        "AsyncClient",
        lambda **kwargs: Client(),
    )

    records = asyncio.run(
        weather.fetch_historical_weather(
            16.5,
            80.6,
            "2020-01-01",
            "2020-01-02",
        )
    )

    assert records == [
        {
            "date": "2020-01-01",
            "max_temperature": 25.0,
            "precipitation_mm": 0.0,
        },
        {
            "date": "2020-01-02",
            "max_temperature": 26.0,
            "precipitation_mm": 4.5,
        },
    ]
    saved_records.assert_awaited_once()
