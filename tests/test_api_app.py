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


def test_attendance_day_events_requires_token_when_configured(tmp_path):
    client = TestClient(create_app(
        db_path=str(tmp_path / "events.db"),
        api_token="secret",
    ))

    response = client.get(
        "/attendance/events/day/?employee_id=100&date=2026-04-20"
    )

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


def test_attendance_analyze_uses_all_events_for_critical_absence_context(tmp_path):
    sqlite_path = tmp_path / "events.db"
    storage = EventStorage(str(tmp_path / "events.ndjson"), str(sqlite_path))
    storage.write_events([
        _event(serial=1, timestamp="2026-04-20T09:00:00"),
        _event(serial=2, timestamp="2026-04-20T18:00:00"),
        _event(employee_id="200", serial=3, timestamp="2026-04-21T09:00:00"),
        _event(employee_id="200", serial=4, timestamp="2026-04-21T18:00:00"),
        _event(serial=5, timestamp="2026-04-22T09:00:00"),
        _event(serial=6, timestamp="2026-04-22T18:00:00"),
    ])
    client = TestClient(create_app(db_path=str(sqlite_path), api_token="secret"))

    response = client.post(
        "/attendance/analyze",
        json=_payload(period_start="2026-04-20", period_end="2026-04-22"),
        headers={"Authorization": "Bearer secret"},
    )

    assert response.status_code == 200
    absence = next(
        record for record in response.json()["records"]
        if record["date"] == "2026-04-21"
    )
    assert "Отсутствие" in absence["employee_issues"]
    assert not any(
        "критического отсутствия" in issue
        for issue in absence["technical_issues"]
    )


def test_api_requests_reuse_repository_engine(tmp_path, monkeypatch):
    sqlite_path = tmp_path / "events.db"
    storage = EventStorage(str(tmp_path / "events.ndjson"), str(sqlite_path))
    storage.write_events([_event(serial=1, timestamp="2026-04-20T09:00:00")])

    import core.repositories.collector_events as collector_events_repo

    call_count = {"value": 0}
    original_factory = collector_events_repo.create_collector_engine

    def _counting_factory(*args, **kwargs):
        call_count["value"] += 1
        return original_factory(*args, **kwargs)

    monkeypatch.setattr(
        collector_events_repo,
        "create_collector_engine",
        _counting_factory,
    )

    client = TestClient(create_app(db_path=str(sqlite_path), api_token="secret"))

    response1 = client.get(
        "/attendance/events/day/?employee_id=100&date=2026-04-20",
        headers={"Authorization": "Bearer secret"},
    )
    response2 = client.get(
        "/attendance/events/day/?employee_id=100&date=2026-04-20",
        headers={"Authorization": "Bearer secret"},
    )

    assert response1.status_code == 200
    assert response2.status_code == 200
    assert call_count["value"] == 1


def test_attendance_day_events_returns_employee_events_for_date(tmp_path):
    sqlite_path = tmp_path / "events.db"
    image_path = tmp_path / "images" / "event.jpg"
    image_path.parent.mkdir()
    image_path.write_bytes(b"fake-jpeg")
    storage = EventStorage(str(tmp_path / "events.ndjson"), str(sqlite_path))
    storage.write_events([
        {
            **_event(serial=2, timestamp="2026-04-20T12:00:00"),
            "_imagePath": str(image_path),
            "_device_name": "Турникет",
        },
        _event(serial=1, timestamp="2026-04-20T09:00:00"),
        _event(employee_id="200", serial=3, timestamp="2026-04-20T10:00:00"),
        _event(serial=4, timestamp="2026-04-21T09:00:00"),
    ])
    client = TestClient(create_app(db_path=str(sqlite_path), api_token="secret"))

    response = client.get(
        "/attendance/events/day/?employee_id=100&date=2026-04-20",
        headers={"Authorization": "Bearer secret"},
    )

    assert response.status_code == 200
    events = response.json()
    assert [event["serial_no"] for event in events] == [1, 2]
    assert events[0]["time_label"] == "09:00:00"
    assert events[0]["caption"] == "Успешный вход"
    assert events[0]["has_photo"] is False
    assert events[1]["device_name"] == "Турникет"
    assert events[1]["has_photo"] is True
    assert events[1]["photo_url"].startswith("/attendance/events/photos/")


def test_attendance_event_photo_returns_saved_file(tmp_path):
    sqlite_path = tmp_path / "events.db"
    image_path = tmp_path / "images" / "event.jpg"
    image_path.parent.mkdir()
    image_path.write_bytes(b"fake-jpeg")
    storage = EventStorage(str(tmp_path / "events.ndjson"), str(sqlite_path))
    storage.write_events([
        {
            **_event(serial=1, timestamp="2026-04-20T09:00:00"),
            "_imagePath": str(image_path),
        }
    ])
    client = TestClient(create_app(db_path=str(sqlite_path), api_token="secret"))
    events_response = client.get(
        "/attendance/events/day/?employee_id=100&date=2026-04-20",
        headers={"Authorization": "Bearer secret"},
    )
    event_key = events_response.json()[0]["event_key"]

    response = client.get(
        f"/attendance/events/photos/{event_key}/",
        headers={"Authorization": "Bearer secret"},
    )

    assert response.status_code == 200
    assert response.content == b"fake-jpeg"
    assert response.headers["content-type"] == "image/jpeg"


def test_attendance_event_photo_rewrites_unc_path_to_local_mount(tmp_path):
    sqlite_path = tmp_path / "events.db"
    image_path = tmp_path / "data" / "images" / "event.jpg"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(b"fake-jpeg")
    storage = EventStorage(str(tmp_path / "events.ndjson"), str(sqlite_path))
    storage.write_events([
        {
            **_event(serial=1, timestamp="2026-04-20T09:00:00"),
            "_imagePath": (
                "\\\\172.11.1.254\\Face_ID\\data\\images\\event.jpg"
            ),
        }
    ])
    core = LogStormCore.from_sources(
        env={
            "LOGSTORM_PHOTO_PATH_REWRITES": (
                "//172.11.1.254/Face_ID=" + str(tmp_path)
            ),
        },
        collector_db_path=str(sqlite_path),
        api_token="secret",
    )
    client = TestClient(create_app(core=core))
    events_response = client.get(
        "/attendance/events/day/?employee_id=100&date=2026-04-20",
        headers={"Authorization": "Bearer secret"},
    )
    event_key = events_response.json()[0]["event_key"]

    response = client.get(
        f"/attendance/events/photos/{event_key}/",
        headers={"Authorization": "Bearer secret"},
    )

    assert response.status_code == 200
    assert response.content == b"fake-jpeg"


def test_attendance_event_photo_returns_404_without_saved_file(tmp_path):
    sqlite_path = tmp_path / "events.db"
    storage = EventStorage(str(tmp_path / "events.ndjson"), str(sqlite_path))
    storage.write_events([
        _event(serial=1, timestamp="2026-04-20T09:00:00"),
    ])
    client = TestClient(create_app(db_path=str(sqlite_path)))
    events_response = client.get(
        "/attendance/events/day/?employee_id=100&date=2026-04-20",
    )
    event_key = events_response.json()[0]["event_key"]

    response = client.get(f"/attendance/events/photos/{event_key}/")

    assert response.status_code == 404


def test_attendance_override_is_saved_and_applied_to_analysis(tmp_path):
    sqlite_path = tmp_path / "events.db"
    storage = EventStorage(str(tmp_path / "events.ndjson"), str(sqlite_path))
    storage.write_events([
        _event(serial=1, timestamp="2026-04-20T09:30:00"),
        _event(serial=2, timestamp="2026-04-20T17:00:00"),
    ])
    client = TestClient(create_app(db_path=str(sqlite_path)))

    override_response = client.patch(
        "/attendance/overrides/100/2026-04-20",
        json={
            "arrival_time": "09:00:00",
            "work_hours": 9,
            "is_late": False,
            "late_minutes": None,
        },
    )

    assert override_response.status_code == 200
    assert override_response.json()["patch"]["arrival_time"] == "09:00:00"

    analyze_response = client.post("/attendance/analyze", json=_payload())

    assert analyze_response.status_code == 200
    record = analyze_response.json()["records"][0]
    assert record["arrival_time"] == "09:00:00"
    assert record["work_hours"] == 9
    assert record["is_late"] is False
    assert record["manual_edited"] is True
    assert record["manual_edit_payload"]["is_late"] is False
    assert not any("late" in issue.lower() for issue in record["employee_issues"])


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
