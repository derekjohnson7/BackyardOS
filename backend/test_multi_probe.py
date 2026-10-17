"""Multiple probes must never share a latest reading or analysis history."""
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

import database
from database import get_session
from main import app, verify_api_key
from models import SensorReading


@pytest.fixture
def client():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    def session_override():
        with Session(engine) as session:
            yield session
    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[verify_api_key] = lambda: None
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()


def payload(probe_id=1, value=50, timestamp=None):
    return dict(device_id='backyard-node-01', probe_id=probe_id,
                timestamp=(timestamp or datetime.utcnow()).isoformat(),
                soil_moisture_raw=2000, soil_moisture_pct=value,
                temperature_c=24, humidity_pct=50, pressure_hpa=1000)


def test_legacy_upload_defaults_to_probe_one(client):
    record = payload()
    del record['probe_id']
    response = client.post('/readings', json=record)
    assert response.status_code == 200
    assert response.json()['probe_id'] == 1
    for invalid in [0, 7, 1.5, None]:
        assert client.post('/readings', json=payload(invalid)).status_code == 422


def test_latest_and_advisor_separate_all_four_probes(client):
    now = datetime.utcnow()
    for probe in range(1, 5):
        for offset, value in [(2, probe * 10), (1, probe * 10 + 1)]:
            response = client.post('/readings', json=payload(probe, value, now - timedelta(minutes=offset)))
            assert response.status_code == 200
    latest = client.get('/readings/latest').json()
    assert {r['probe_id']: r['soil_moisture_pct'] for r in latest} == {1: 11, 2: 21, 3: 31, 4: 41}
    assert len(client.get('/readings').json()) == 8
    for endpoint in ['/advisor', '/advisor/trends']:
        result = client.get(endpoint)
        assert result.status_code == 200, result.text
        assert {r['probe_id'] for r in result.json()} == {1, 2, 3, 4}
    findings = client.get('/advisor/analysis').json()['findings']
    trends = [f for f in findings if f['id'].endswith('-TREND')]
    temps = [f for f in findings if f['id'].endswith('-TEMP')]
    assert len(trends) == len(temps) == 4
    assert all(f['net_change_percentage_points'] == 1 for f in trends)
    assert all(f['valid_readings'] == 2 for f in temps)
    assert len({f['id'] for f in findings}) == 8


def test_startup_migrates_existing_rows_and_is_repeatable():
    engine = create_engine('sqlite://', poolclass=StaticPool)
    with engine.begin() as connection:
        connection.execute(text('CREATE TABLE sensorreading (id INTEGER PRIMARY KEY, device_id TEXT)'))
        connection.execute(text("INSERT INTO sensorreading VALUES (1, 'old-node')"))
    with patch.object(database, 'engine', engine):
        database.create_db_and_tables()
        database.create_db_and_tables()
    with engine.connect() as connection:
        assert connection.execute(text('SELECT device_id, probe_id FROM sensorreading')).one() == ('old-node', 1)
        connection.execute(text("INSERT INTO sensorreading (id,device_id) VALUES (2,'legacy-firmware')"))
        assert connection.execute(text('SELECT probe_id FROM sensorreading WHERE id=2')).scalar() == 1
    engine.dispose()


def test_historical_correlations_keep_opposite_probe_histories_separate():
    from advisor_data import prepare_sensor_readings, prepare_moisture_inputs
    from advisor_analysis import build_moisture_findings, build_temperature_findings
    records = []
    now = datetime.utcnow()
    for index in range(30):
        for probe in (1, 2):
            row = payload(probe, index if probe == 1 else 100 - index, now + timedelta(minutes=index))
            row['temperature_c'] = index
            records.append(row)
    prepared = prepare_sensor_readings(records)
    summaries, histories = prepare_moisture_inputs(prepared)
    trends = build_moisture_findings(summaries, histories)
    temperatures = build_temperature_findings(prepared)
    assert {f['probe_id']: f['net_change_percentage_points'] for f in trends} == {1: 29, 2: -29}
    assert {f['probe_id']: f['overall_correlation'] for f in temperatures} == {1: 1.0, 2: -1.0}
    assert all(f['valid_readings'] == 30 for f in temperatures)
