import os

from fastapi import FastAPI, Depends, Header, HTTPException
from sqlmodel import Session, select

from database import create_db_and_tables, get_session
from models import SensorReading, SensorReadingCreate
from fastapi.middleware.cors import CORSMiddleware

from dotenv import load_dotenv
import requests
from datetime import datetime, timedelta

from advisor import analyze_reading, analyze_trend

from advisor_data import (
    prepare_sensor_readings,
    prepare_moisture_inputs,
)

from advisor_analysis import (
    build_moisture_findings,
    build_temperature_findings,
)

weather_cache = {
    "data": None,
    "timestamp": None,
}

WEATHER_CACHE_TTL = timedelta(minutes=15)

load_dotenv()

API_KEY = os.getenv("API_KEY")
WEATHER_LATITUDE = os.getenv("WEATHER_LATITUDE")
WEATHER_LONGITUDE = os.getenv("WEATHER_LONGITUDE")

def advisor_current_time():
    """Return the current UTC time for historical analysis."""
    return datetime.utcnow()

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

@app.get("/readings")
def get_readings(session: Session = Depends(get_session)):
    cutoff = datetime.utcnow() - timedelta(days=7)

    readings = session.exec(
        select(SensorReading)
        .where(SensorReading.timestamp >= cutoff)
        .order_by(SensorReading.timestamp.asc())
    ).all()

    return readings

@app.get("/readings/latest")
def get_latest_readings(session: Session = Depends(get_session)):
    device_ids = session.exec(
        select(SensorReading.device_id).distinct()
    ).all()

    latest_readings = []

    for device_id in device_ids:
        reading = session.exec(
            select(SensorReading)
            .where(SensorReading.device_id == device_id)
            .order_by(SensorReading.timestamp.desc())
            .limit(1)
        ).first()

        if reading is not None:
            latest_readings.append(reading)

    return latest_readings

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

    url = "https://api.weatherapi.com/v1/forecast.json"

    params = {
        "key": api_key,
        "q": f"{latitude},{longitude}",
        "days": 1,
        "aqi": "no",
        "alerts": "no",
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
    forecast_day = data["forecast"]["forecastday"][0]

    weather_data = {
    "temperature_f": current["temp_f"],
    "feels_like_f": current["feelslike_f"],
    "heat_index_f": current["heatindex_f"],
    "humidity_pct": current["humidity"],
    "dew_point_f": current["dewpoint_f"],
    "uv_index": current["uv"],
    "precipitation_in": current["precip_in"],
    "weather_code": current["condition"]["code"],
    "condition": current["condition"]["text"],
    "wind_speed_mph": current["wind_mph"],
    "wind_gust_mph": current["gust_mph"],
    "wind_direction": current["wind_dir"],

    "high_temp_f": forecast_day["day"]["maxtemp_f"],
    "low_temp_f": forecast_day["day"]["mintemp_f"],
    "chance_of_rain_pct": forecast_day["day"]["daily_chance_of_rain"],
    "total_precipitation_in": forecast_day["day"]["totalprecip_in"],

    "sunrise": forecast_day["astro"]["sunrise"],
    "sunset": forecast_day["astro"]["sunset"],
    }

    weather_cache["data"] = weather_data
    weather_cache["timestamp"] = now

    return weather_data

@app.get("/advisor")
def get_advisor(session: Session = Depends(get_session)):
    device_ids = session.exec(
        select(SensorReading.device_id).distinct()
    ).all()

    results = []

    for device_id in device_ids:
        reading = session.exec(
            select(SensorReading)
            .where(SensorReading.device_id == device_id)
            .order_by(SensorReading.timestamp.desc())
            .limit(1)
        ).first()

        if reading is not None:
            results.append(analyze_reading(reading))

    return results

@app.get("/advisor/trends")
def get_advisor_trends(
    hours: int = 24,
    session: Session = Depends(get_session)
):
    if hours not in (24, 72):
        raise HTTPException(
            status_code=400,
            detail="Supported trend windows are 24 and 72 hours."
        )

    cutoff = datetime.utcnow() - timedelta(hours=hours)

    device_ids = session.exec(
        select(SensorReading.device_id).distinct()
    ).all()

    results = []

    for device_id in device_ids:
        readings = session.exec(
            select(SensorReading)
            .where(SensorReading.device_id == device_id)
            .where(SensorReading.timestamp >= cutoff)
            .order_by(SensorReading.timestamp.asc())
        ).all()

        if readings:
            results.append(analyze_trend(readings))

    return results

@app.get("/advisor/analysis")
def get_advisor_analysis(
    days: int = 7,
    session: Session = Depends(get_session),
):
    """
    Generate verified historical sensor findings.

    Read-only. Does not invoke Ollama or modify sensor data.
    """
    if days < 2 or days > 30:
        raise HTTPException(
            status_code=400,
            detail="Supported analysis windows are 2 to 30 days.",
        )

    cutoff = advisor_current_time() - timedelta(days=days)

    readings = session.exec(
        select(SensorReading)
        .where(SensorReading.timestamp >= cutoff)
        .order_by(
            SensorReading.device_id,
            SensorReading.timestamp,
        )
    ).all()

    if not readings:
        return {
            "status": "insufficient_data",
            "analysis_window_days": days,
            "reading_count": 0,
            "findings": [],
            "message": "No readings found in the requested window.",
        }

    prepared = prepare_sensor_readings(readings)
    summaries, histories = prepare_moisture_inputs(prepared)

    findings = (
        build_moisture_findings(summaries, histories)
        + build_temperature_findings(prepared)
    )

    return {
        "status": "ok",
        "analysis_window_days": days,
        "reading_count": len(prepared),
        "findings": findings,
    }