from fastapi import FastAPI, Depends
from sqlmodel import Session, select

from database import create_db_and_tables, get_session
from models import SensorReading, SensorReadingCreate

app = FastAPI()


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.get("/")
def home():
    return "Hello BackyardOS"


@app.post("/readings")
def create_reading(
    reading: SensorReadingCreate,
    session: Session = Depends(get_session)
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
