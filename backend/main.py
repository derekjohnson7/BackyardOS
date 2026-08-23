import os

from fastapi import FastAPI, Depends, Header, HTTPException
from sqlmodel import Session, select

from database import create_db_and_tables, get_session
from models import SensorReading, SensorReadingCreate
from fastapi.middleware.cors import CORSMiddleware

API_KEY = os.getenv("API_KEY")


app = FastAPI(
     docs_url="/docs",
     redoc_url="/redoc",
     openapi_url="/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
		"https://backyardos-dash.onrender.com/",
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
def get_readings(
	session: Session = Depends(get_session)
):
	statement = select(SensorReading)
	readings = session.exec(statement).all()
	
	return readings
