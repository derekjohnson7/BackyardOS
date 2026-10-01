
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from database import get_session
from main import app
from models import SensorReading


# Temporary in-memory SQLite database
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=__import__(
        "sqlalchemy.pool",
        fromlist=["StaticPool"]
    ).StaticPool,
)

SQLModel.metadata.create_all(engine)


def test_session():
    with Session(engine) as session:
        yield session


app.dependency_overrides[get_session] = test_session

with Session(engine) as session:
    session.add(
        SensorReading(
            device_id="backyard-test-01",
            timestamp=datetime.now(timezone.utc),
            soil_moisture_raw=1200,
            soil_moisture_pct=92,
            temperature_c=40,
            humidity_pct=65,
            pressure_hpa=1013,
        )
    )
    session.commit()

with TestClient(app) as client:
    response = client.get("/advisor")

    print("HTTP status:", response.status_code)
    print("Advisor response:", response.json())

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["observation_count"] == 2

print("\nAdvisor API test PASSED")

app.dependency_overrides.clear()
