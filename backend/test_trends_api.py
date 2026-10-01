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
    # Generate 72 hours of continuous readings.
    # The newest reading is approximately current.
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    with Session(engine) as session:
        for i in range(433):
            reading = SensorReading(
                device_id="backyard-test-01",
                timestamp=now - timedelta(minutes=(432 - i) * 10),
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
        # Verify the default endpoint uses the 24-hour recommendation
    assert "24 hours" in result["observations"][0]["message"]
    assert "72 hours" not in result["observations"][0]["message"]
    assert "recommendation" in result["observations"][0]

    # Verify explicit 24-hour window
    response_24 = client.get("/advisor/trends?hours=24")

    assert response_24.status_code == 200
    assert response_24.json()[0]["status"] == "ok"

    print("24-hour endpoint: PASSED")

    # Verify 72-hour window
    response_72 = client.get("/advisor/trends?hours=72")

    assert response_72.status_code == 200
    assert response_72.json()[0]["status"] == "ok"
    result_72 = response_72.json()[0]

    assert result_72["duration_hours"] >= 71.5
    assert result_72["reading_count"] >= 430
    assert result_72["data_continuous"] is True
    assert len(result_72["observations"]) == 1
    # Verify the multi-day recommendation is selected
    assert "72 hours" in result_72["observations"][0]["message"]
    assert "multiple depths" in result_72["observations"][0]["recommendation"]

    print("72-hour duration:", result_72["duration_hours"])
    print("72-hour readings:", result_72["reading_count"])

    print("72-hour endpoint: PASSED")

    # Reject unsupported time windows
    response_invalid = client.get("/advisor/trends?hours=500")

    assert response_invalid.status_code == 400

    print("Invalid window protection: PASSED")

    print("\nAdvisor Trend API test PASSED")

finally:
    app.dependency_overrides.pop(get_session, None)
    engine.dispose()