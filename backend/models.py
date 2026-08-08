from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class SensorReadingCreate(SQLModel):
    device_id: str
    timestamp: datetime
    soil_moisture_raw: int
    soil_moisture_pct: float
    temperature_c: float
    humidity_pct: float
    pressure_hpa: float


class SensorReading(SensorReadingCreate, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
