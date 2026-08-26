import os

from fastapi import FastAPI, Depends, Header, HTTPException
from sqlmodel import Session, select

from database import create_db_and_tables, get_session
from models import SensorReading, SensorReadingCreate
from fastapi.middleware.cors import CORSMiddleware

from dotenv import load_dotenv
import requests
from datetime import datetime, timedelta

weather_cache = {
    "data": None,
    "timestamp": None,
}

WEATHER_CACHE_TTL = timedelta(minutes=15)

load_dotenv()

API_KEY = os.getenv("API_KEY")
WEATHER_LATITUDE = os.getenv("WEATHER_LATITUDE")
WEATHER_LONGITUDE = os.getenv("WEATHER_LONGITUDE")


app = FastAPI(
     docs_url="/docs",
     redoc_url="/redoc",
     openapi_url="/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
		"https://backyardos-dash.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

def verify_api_key(x_api_key: str = Header(...)):
    if API_KEY is None:
        raise HTTPException(
            status_code=500,
            detail="API key is not configured"
        )

    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )

@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.get("/")
def home():
    return "Hello BackyardOS"


@app.post("/readings")
def create_reading(
    reading: SensorReadingCreate,
    session: Session = Depends(get_session),
    _: None = Depends(verify_api_key)
):
    db_reading = SensorReading(**reading.model_dump())

    session.add(db_reading)
    session.commit()
    session.refresh(db_reading)

    return db_reading


@app.get("/weather")
def get_weather():
    latitude = os.getenv("WEATHER_LATITUDE")
    longitude = os.getenv("WEATHER_LONGITUDE")
    api_key = os.getenv("WEATHER_API_KEY")

    if not latitude or not longitude:
        raise HTTPException(
            status_code=500,
            detail="Weather location is not configured"
        )

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="Weather API key is not configured"
        )

    now = datetime.utcnow()

    if (
        weather_cache["data"] is not None
        and weather_cache["timestamp"] is not None
        and now - weather_cache["timestamp"] < WEATHER_CACHE_TTL
    ):
        return weather_cache["data"]

    url = "https://api.weatherapi.com/v1/current.json"

    params = {
        "key": api_key,
        "q": f"{latitude},{longitude}",
        "aqi": "no",
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

    except requests.RequestException:
        raise HTTPException(
            status_code=502,
            detail="Unable to retrieve weather data"
        )

    data = response.json()
    current = data["current"]

    weather_data = {
        "temperature_f": current["temp_f"],
        "humidity_pct": current["humidity"],
        "precipitation_in": current["precip_in"],
        "weather_code": current["condition"]["code"],
        "condition": current["condition"]["text"],
        "wind_speed_mph": current["wind_mph"],
    }

    weather_cache["data"] = weather_data
    weather_cache["timestamp"] = now

    return weather_data