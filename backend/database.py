
import os
import hashlib
import json
from datetime import datetime, timezone

from dotenv import load_dotenv
from pymongo import AsyncMongoClient
from pymongo.errors import PyMongoError

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
DATABASE_NAME = os.getenv(
    "MONGODB_DATABASE",
    "climate_analyzer",
)

client = (
    AsyncMongoClient(
        MONGODB_URI,
        serverSelectionTimeoutMS=5000,
    )
    if MONGODB_URI
    else None
)

db = client[DATABASE_NAME] if client is not None else None
weather_cache = db["weather_cache"] if db is not None else None


def make_cache_key(latitude, longitude, start_date, end_date):
    payload = {
        "latitude": round(latitude, 4),
        "longitude": round(longitude, 4),
        "start_date": start_date,
        "end_date": end_date,
        "variable": "temperature_2m_max",
        "source": "open-meteo-archive",
    }

    serialized = json.dumps(payload, sort_keys=True)

    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()


async def get_cached_weather(
    cache_key,
    latitude,
    longitude,
    start_date,
    end_date,
):
    if weather_cache is None:
        return None

    try:
        # 1. Try an exact cache-key match first.
        document = await weather_cache.find_one({"_id": cache_key})

        # 2. If no exact match, find a cached range
        # that completely contains the requested range.
        if document is None:
            document = await weather_cache.find_one(
                {
                    "latitude": round(latitude, 4),
                    "longitude": round(longitude, 4),
                    "start_date": {"$lte": start_date},
                    "end_date": {"$gte": end_date},
                },
                sort=[
                    ("start_date", -1),
                    ("end_date", 1),
                ],
            )

        if document is None:
            return None

        # Return only records inside the requested dates.
        records = document["records"]

        return [
            record
            for record in records
            if start_date <= record["date"] <= end_date
        ]

    except PyMongoError as exc:
        print(f"MongoDB cache read failed: {exc}")
        return None



async def save_cached_weather(
    cache_key,
    latitude,
    longitude,
    start_date,
    end_date,
    records,
):
    if weather_cache is None:
        return

    try:
        await weather_cache.update_one(
            {"_id": cache_key},
            {
                "$set": {
                    "latitude": round(latitude, 4),
                    "longitude": round(longitude, 4),
                    "start_date": start_date,
                    "end_date": end_date,
                    "records": records,
                    "fetched_at": datetime.now(timezone.utc),
                }
            },
            upsert=True,
        )

    except PyMongoError as exc:
        print(f"MongoDB cache write failed: {exc}")


async def check_database():
    if client is None:
        return False

    try:
        await client.admin.command("ping")
        return True
    except PyMongoError:
        return False


async def close_database():
    if client is not None:
        await client.close()
