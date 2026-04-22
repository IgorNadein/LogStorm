import json
from datetime import date

import pandas as pd

from collector.storage import EventStorage
from analyzer import AttendanceAnalysisRequest, DataLoader, EusrrAttendanceService


def _collector_event(employee_id, serial, timestamp):
    return {
        "_device": "door-1",
        "_collected": "2026-04-20T10:00:00",
        "major": 5,
        "minor": 75,
        "time": timestamp,
        "employeeNoString": str(employee_id),
        "serialNo": serial,
        "name": str(employee_id),
    }


def _request(date_overrides=None):
    return AttendanceAnalysisRequest.from_dict({
        "employee_id": "100",
        "period_start": "2026-04-20",
        "period_end": "2026-04-26",
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
            "date_overrides": date_overrides or [],
        },
    })


def test_sqlite_to_attendance_response_with_weekend_override(tmp_path):
    sqlite_path = tmp_path / "events.db"
    storage = EventStorage(str(tmp_path / "events.ndjson"), str(sqlite_path))
    storage.write_events([
        _collector_event("100", 1, "2026-04-20T09:00:00"),
        _collector_event("100", 2, "2026-04-20T18:00:00"),
        _collector_event("100", 3, "2026-04-25T09:30:00"),
        _collector_event("100", 4, "2026-04-25T18:00:00"),
    ])

    df = DataLoader.load_logs(str(sqlite_path), file_type="sqlite")
    response = EusrrAttendanceService(df).analyze(_request([
        {"date": "2026-04-25", "is_workday": True}
    ]))
    records = {record.date: record for record in response.records}

    assert records[date(2026, 4, 20)].work_hours == 9
    assert records[date(2026, 4, 25)].is_workday is True
    assert records[date(2026, 4, 25)].is_late is True


def test_ndjson_to_attendance_response_with_holiday_override(tmp_path):
    ndjson = tmp_path / "events.ndjson"
    events = [
        _collector_event("100", 1, "2026-04-20T11:00:00"),
        _collector_event("100", 2, "2026-04-20T13:00:00"),
    ]
    ndjson.write_text(
        "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in events),
        encoding="utf-8",
    )

    df = DataLoader.load_logs(str(ndjson), file_type="ndjson")
    response = EusrrAttendanceService(df).analyze(_request([
        {"date": "2026-04-20", "is_workday": False}
    ]))
    record = response.records[0]

    assert record.is_workday is False
    assert record.is_overtime is True
    assert record.is_late is False


def test_csv_to_attendance_response(tmp_path):
    csv_path = tmp_path / "events.csv"
    pd.DataFrame([
        {"timestamp": "2026-04-20T09:00:00", "name": "100"},
        {"timestamp": "2026-04-20T18:00:00", "name": "100"},
    ]).to_csv(csv_path, index=False)

    df = DataLoader.load_logs(str(csv_path), file_type="csv")
    response = EusrrAttendanceService(df).analyze(_request(
        date_overrides=[{"date": "2026-04-26", "is_workday": True}]
    ))

    assert len(response.records) == 7
    assert response.records[0].work_hours == 9
