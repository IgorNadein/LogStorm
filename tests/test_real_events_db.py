import sqlite3

import pytest

from services import (
    AttendanceAnalysisRequest,
    DataLoader,
    EusrrAttendanceService,
    CollectorEventRepository,
)


@pytest.mark.realdb
def test_real_db_schema_matches_collector_models(real_db_path):
    conn = sqlite3.connect(real_db_path)
    try:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        columns = {row[1] for row in conn.execute("PRAGMA table_info(events)")}
    finally:
        conn.close()

    assert {"events", "collector_state"}.issubset(tables)
    assert {
        "device",
        "serialNo",
        "time",
        "employeeNoString",
        "name",
        "event_data",
        "collected_at",
    }.issubset(columns)


@pytest.mark.realdb
def test_real_db_reads_events_by_employee_and_period(real_db_path):
    repo = CollectorEventRepository(str(real_db_path))
    sample = repo.load_raw_events(limit=1)
    assert sample

    employee_id = str(sample[0]["employeeNoString"])
    event_date = sample[0]["time"][:10]
    events = repo.load_raw_events(
        start=event_date,
        end=event_date + "T23:59:59",
        employee_id=employee_id,
        limit=10,
    )

    assert events
    assert all(str(event["employeeNoString"]) == employee_id for event in events)


@pytest.mark.realdb
def test_real_db_can_run_single_employee_analysis(real_db_path):
    repo = CollectorEventRepository(str(real_db_path))
    sample = repo.load_raw_events(limit=1)
    assert sample

    employee_id = str(sample[0]["employeeNoString"])
    event_date = sample[0]["time"][:10]
    df = DataLoader.load_logs(str(real_db_path), file_type="sqlite")
    request = AttendanceAnalysisRequest.from_dict({
        "employee_id": employee_id,
        "period_start": event_date,
        "period_end": event_date,
        "schedule": {
            "start_time": "09:00",
            "end_time": "18:00",
            "expected_hours": 9,
            "workdays": [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
            ],
            "date_overrides": [],
        },
    })

    response = EusrrAttendanceService(df).analyze(request)

    assert len(response.records) == 1
    assert response.records[0].user_name == employee_id
