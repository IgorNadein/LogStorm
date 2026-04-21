from collector.storage import EventStorage
from core import LogStormCore
from fastapi.testclient import TestClient

from api.app import create_app


def _event(employee_id="100", serial=1, timestamp="2026-04-20T09:00:00"):
    return {
        "_device": "door-1",
        "_collected": "2026-04-20T10:00:00",
        "major": 5,
        "minor": 75,
        "time": timestamp,
        "employeeNoString": employee_id,
        "serialNo": serial,
        "name": employee_id,
    }


def _payload(**overrides):
    payload = {
        "employee_id": "100",
        "display_name": "Employee Sample",
        "period_start": "2026-04-20",
        "period_end": "2026-04-20",
        "schedule": {
            "start_time": "09:00",
            "end_time": "18:00",
            "expected_hours": 9,
            "workdays": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            "date_overrides": [],
        },
    }
    payload.update(overrides)
    return payload


def _payload_without_schedule():
    payload = _payload()
    payload.pop("schedule")
    return payload


def test_health_endpoint(tmp_path):
    client = TestClient(create_app(db_path=str(tmp_path / "events.db")))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_attendance_analyze_requires_token_when_configured(tmp_path):
    client = TestClient(create_app(
        db_path=str(tmp_path / "events.db"),
        api_token="secret",
    ))

    response = client.post("/attendance/analyze", json=_payload())

    assert response.status_code == 401


def test_attendance_analyze_reads_sqlite_and_returns_api_shape(tmp_path):
    sqlite_path = tmp_path / "events.db"
    storage = EventStorage(str(tmp_path / "events.ndjson"), str(sqlite_path))
    storage.write_events([
        _event(serial=1, timestamp="2026-04-20T09:00:00"),
        _event(serial=2, timestamp="2026-04-20T18:00:00"),
        _event(employee_id="200", serial=3, timestamp="2026-04-20T09:00:00"),
    ])
    client = TestClient(create_app(db_path=str(sqlite_path), api_token="secret"))

    response = client.post(
        "/attendance/analyze",
        json=_payload(),
        headers={"Authorization": "Bearer secret"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["employee_id"] == "100"
    assert data["period_start"] == "2026-04-20"
    assert len(data["records"]) == 1
    record = data["records"][0]
    assert record["employee_id"] == "100"
    assert record["date"] == "2026-04-20"
    assert record["arrival_time"] == "09:00:00"
    assert record["departure_time"] == "18:00:00"
    assert record["work_hours"] == 9


def test_attendance_analyze_applies_date_overrides(tmp_path):
    sqlite_path = tmp_path / "events.db"
    storage = EventStorage(str(tmp_path / "events.ndjson"), str(sqlite_path))
    storage.write_events([
        _event(serial=1, timestamp="2026-04-20T11:00:00"),
        _event(serial=2, timestamp="2026-04-20T13:00:00"),
    ])
    client = TestClient(create_app(db_path=str(sqlite_path)))
    payload = _payload(schedule={
        "start_time": "09:00",
        "end_time": "18:00",
        "expected_hours": 9,
        "workdays": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        "date_overrides": [
            {"date": "2026-04-20", "is_workday": False, "reason": "holiday"}
        ],
    })

    response = client.post("/attendance/analyze", json=payload)

    assert response.status_code == 200
    record = response.json()["records"][0]
    assert record["is_workday"] is False
    assert record["is_overtime"] is True
    assert record["is_late"] is False


def test_attendance_analyze_uses_default_schedule_when_missing(tmp_path):
    sqlite_path = tmp_path / "events.db"
    storage = EventStorage(str(tmp_path / "events.ndjson"), str(sqlite_path))
    storage.write_events([
        _event(serial=1, timestamp="2026-04-20T08:00:00"),
        _event(serial=2, timestamp="2026-04-20T17:00:00"),
    ])
    client = TestClient(create_app(db_path=str(sqlite_path)))

    response = client.post("/attendance/analyze", json=_payload_without_schedule())

    assert response.status_code == 200
    record = response.json()["records"][0]
    assert record["schedule_start"] == "08:00"
    assert record["schedule_end"] == "17:00"
    assert record["expected_hours"] == 9


def test_attendance_analyze_rejects_missing_schedule_when_fallback_disabled(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("LOGSTORM_ALLOW_DEFAULT_SCHEDULE", "false")
    client = TestClient(create_app(db_path=str(tmp_path / "events.db")))

    response = client.post("/attendance/analyze", json=_payload_without_schedule())

    assert response.status_code == 422
    assert "schedule is required" in response.json()["detail"]


def test_attendance_analyze_default_schedule_can_be_configured_by_env(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("LOGSTORM_DEFAULT_START_TIME", "10:00")
    monkeypatch.setenv("LOGSTORM_DEFAULT_END_TIME", "19:00")
    monkeypatch.setenv("LOGSTORM_DEFAULT_EXPECTED_HOURS", "8")
    monkeypatch.setenv("LOGSTORM_DEFAULT_WORKDAYS", "Monday")
    sqlite_path = tmp_path / "events.db"
    storage = EventStorage(str(tmp_path / "events.ndjson"), str(sqlite_path))
    storage.write_events([
        _event(serial=1, timestamp="2026-04-20T10:00:00"),
        _event(serial=2, timestamp="2026-04-20T19:00:00"),
    ])
    client = TestClient(create_app(db_path=str(sqlite_path)))

    response = client.post("/attendance/analyze", json=_payload_without_schedule())

    assert response.status_code == 200
    record = response.json()["records"][0]
    assert record["schedule_start"] == "10:00"
    assert record["schedule_end"] == "19:00"
    assert record["expected_hours"] == 8


def test_attendance_analyze_can_use_explicit_core_settings(tmp_path):
    sqlite_path = tmp_path / "events.db"
    storage = EventStorage(str(tmp_path / "events.ndjson"), str(sqlite_path))
    storage.write_events([
        _event(serial=1, timestamp="2026-04-20T10:00:00"),
        _event(serial=2, timestamp="2026-04-20T19:00:00"),
    ])
    core = LogStormCore.from_sources(
        env={
            "LOGSTORM_DEFAULT_START_TIME": "10:00",
            "LOGSTORM_DEFAULT_END_TIME": "19:00",
            "LOGSTORM_DEFAULT_EXPECTED_HOURS": "8",
            "LOGSTORM_DEFAULT_WORKDAYS": "Monday",
        },
        collector_db_path=str(sqlite_path),
    )
    client = TestClient(create_app(core=core))

    response = client.post("/attendance/analyze", json=_payload_without_schedule())

    assert response.status_code == 200
    record = response.json()["records"][0]
    assert record["schedule_start"] == "10:00"
    assert record["schedule_end"] == "19:00"
    assert record["expected_hours"] == 8
