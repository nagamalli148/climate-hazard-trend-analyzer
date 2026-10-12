
import httpx

from database import (
    make_cache_key,
    get_cached_weather,
    save_cached_weather,
)

WEATHER_API_URL = (
    "https://archive-api.open-meteo.com/v1/archive"
)


async def fetch_historical_weather(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
):
    cache_key = make_cache_key(
        latitude,
        longitude,
        start_date,
        end_date,
    )

    # 1. Check MongoDB before calling the external API.
    cached_records = await get_cached_weather(
    cache_key,
    latitude,
    longitude,
    start_date,
    end_date,
)

    if cached_records is not None:
        print("Weather cache: HIT")
        return cached_records

    print("Weather cache: MISS")

    # 2. Fetch data only when it is not cached.
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "temperature_2m_max",
        "timezone": "auto",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            WEATHER_API_URL,
            params=params,
        )
        response.raise_for_status()
        data = response.json()

    daily = data.get("daily", {})
    dates = daily.get("time", [])
    temperatures = daily.get("temperature_2m_max", [])

    if len(dates) != len(temperatures):
        raise ValueError(
            "Weather data has inconsistent lengths"
        )

    records = [
        {
            "date": day,
            "max_temperature": temperature,
        }
        for day, temperature in zip(dates, temperatures)
    ]
    
    # 3. Cache successful responses for future requests.
    await save_cached_weather(cache_key,latitude,longitude,start_date,end_date,records)

    return records
