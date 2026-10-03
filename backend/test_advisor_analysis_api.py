import json
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

from database import get_session
from unittest.mock import patch
from main import app
from models import SensorReading
from advisor_analysis import analyze_daily_trend


def test_historical_analysis():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    data_file = (
        Path(__file__).resolve().parent.parent
        / "backyard_readings_test.json"
    )

    readings = json.loads(
        data_file.read_text(encoding="utf-8")
    )

    with Session(engine) as session:
        for record in readings:
            fields = {
                key: value
                for key, value in record.items()
                if key in SensorReading.model_fields
                and key != "id"
            }

            fields["timestamp"] = datetime.fromisoformat(
                fields["timestamp"]
            )

            session.add(SensorReading(**fields))

        session.commit()

    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session

    try:
        with patch(
            "main.advisor_current_time",
            return_value=datetime(2026, 10, 2, 23, 59, 59),
        ):
            with TestClient(app) as client:
                response = client.get(
                    "/advisor/analysis",
                    params={"days": 8},
                )

        assert response.status_code == 200, response.text
        result = response.json()

        assert result["status"] == "ok"
        print("Readings within analysis window:", result["reading_count"])
        assert result["reading_count"] == 2009

        findings = {
            finding["id"]: finding
            for finding in result["findings"]
        }

        assert set(findings) == {
            "N01-TREND",
            "N02-TREND",
            "N01-TEMP",
            "N02-TEMP",
        }

        assert findings["N01-TREND"]["daily_direction"] == "mixed"
        assert (
            findings["N02-TREND"]["daily_direction"]
            == "consistently_decreasing"
        )

        assert findings["N01-TEMP"]["overall_correlation"] == -0.859
        assert findings["N02-TEMP"]["overall_correlation"] == 0.463

        print("Historical readings:", result["reading_count"])
        print("Verified findings:", len(findings))
        print("ADVISOR HISTORICAL API TEST: PASSED")

    finally:
        app.dependency_overrides.clear()
        engine.dispose()

def test_sparse_data():
    sparse_data = [
        {
            "date": "2026-10-01",
            "average_moisture_pct": 45.0,
            "reading_count": 12,
        },
        {
            "date": "2026-10-02",
            "average_moisture_pct": 40.0,
            "reading_count": 18,
        },
    ]

    result = analyze_daily_trend(sparse_data)

    assert result["direction"] == "insufficient_data"
    assert result["daily_range_points"] is None
    assert result["increasing_intervals"] == 0
    assert result["decreasing_intervals"] == 0
    assert result["unchanged_intervals"] == 0

    print("SPARSE DATA TEST: PASSED")

if __name__ == "__main__":
    test_historical_analysis()
    test_sparse_data()