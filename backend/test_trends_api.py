from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

from main import app, get_session
from models import SensorReading


# Temporary in-memory database; no production data is touched.
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

SQLModel.metadata.create_all(engine)


def test_session():
    with Session(engine) as session:
        yield session


app.dependency_overrides[get_session] = test_session

try:
    # Generate 24 hours of continuous readings.
    # The newest reading is approximately current.
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    with Session(engine) as session:
        for i in range(145):
            reading = SensorReading(
                device_id="backyard-test-01",
                timestamp=now - timedelta(minutes=(144 - i) * 10),
                soil_moisture_raw=1950,
                soil_moisture_pct=70.0,
                temperature_c=25.0,
                humidity_pct=50.0,
                pressure_hpa=1013.0,
            )
            session.add(reading)

        session.commit()

    client = TestClient(app)
    response = client.get("/advisor/trends")

    print("HTTP status:", response.status_code)
    print("Trend API response:", response.json())

    assert response.status_code == 200

    results = response.json()
    assert len(results) == 1

    result = results[0]

    assert result["device_id"] == "backyard-test-01"
    assert result["status"] == "ok"
    assert result["data_continuous"] is True
    assert result["trend"] == "stable"
    assert len(result["observations"]) == 1
    assert "recommendation" in result["observations"][0]

    print("\nAdvisor Trend API test PASSED")

finally:
    app.dependency_overrides.pop(get_session, None)
    engine.dispose()