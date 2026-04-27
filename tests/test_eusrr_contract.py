from datetime import date

import pandas as pd
import pytest

from analyzer import AttendanceAnalysisRequest, EusrrAttendanceService


def _df(rows):
    data = []
    for employee_id, timestamp in rows:
        ts = pd.Timestamp(timestamp)
        data.append({
            "timestamp": ts,
            "date": ts.date(),
            "time": ts.time(),
            "name": str(employee_id),
            "display_name": str(employee_id),
            "event_type": "pass_in",
            "is_valid_pass": True,
        })
    return pd.DataFrame(data)


def _request(**overrides):
    payload = {
        "employee_id": "100",
        "display_name": "Employee Sample",
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
            "date_overrides": [],
        },
    }
    payload.update(overrides)
    return AttendanceAnalysisRequest.from_dict(payload)


def test_request_uses_employee_id_and_returns_each_date_in_period():
    service = EusrrAttendanceService(_df([
        ("100", "2026-04-20T09:00:00"),
        ("100", "2026-04-20T18:00:00"),
        ("200", "2026-04-20T09:00:00"),
    ]))

    response = service.analyze(_request())

    assert response.employee_id == "100"
    assert len(response.records) == 7
    first = response.records[0]
    assert first.date == date(2026, 4, 20)
    assert first.user_name == "100"
    assert first.display_name == "Employee Sample"
    assert first.appearances == 2


def test_schedule_from_request_overrides_local_person_mapping_assumption():
    service = EusrrAttendanceService(_df([
        ("100", "2026-04-20T10:00:00"),
        ("100", "2026-04-20T18:00:00"),
    ]))
    request = _request(schedule={
        "start_time": "10:00",
        "end_time": "18:00",
        "expected_hours": 8,
        "workdays": ["Monday"],
        "date_overrides": [],
    })

    record = service.analyze(request).records[0]

    assert record.schedule_start.hour == 10
    assert record.expected_hours == 8
    assert record.is_late is False


def test_date_overrides_make_weekday_holiday_and_weekend_workday():
    service = EusrrAttendanceService(_df([
        ("100", "2026-04-20T11:00:00"),
        ("100", "2026-04-20T13:00:00"),
        ("100", "2026-04-25T09:30:00"),
        ("100", "2026-04-25T18:00:00"),
    ]))
    request = _request(schedule={
        "start_time": "09:00",
        "end_time": "18:00",
        "expected_hours": 9,
        "workdays": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        "date_overrides": [
            {"date": "2026-04-20", "is_workday": False, "reason": "holiday"},
            {
                "date": "2026-04-25",
                "is_workday": True,
                "reason": "transferred_workday",
            },
        ],
    })

    records = {record.date: record for record in service.analyze(request).records}

    holiday = records[date(2026, 4, 20)]
    assert holiday.is_workday is False
    assert holiday.is_overtime is True
    assert holiday.is_late is False
    assert holiday.is_underwork is False

    transferred = records[date(2026, 4, 25)]
    assert transferred.is_workday is True
    assert transferred.is_late is True
    assert transferred.is_underwork is True


def test_employee_without_events_gets_absence_only_on_workdays():
    response = EusrrAttendanceService(_df([])).analyze(_request())

    records = {record.date: record for record in response.records}

    assert records[date(2026, 4, 20)].is_underwork is False
    assert "Отсутствие" in records[date(2026, 4, 20)].employee_issues
    assert records[date(2026, 4, 25)].employee_issues == []


def test_employee_absence_is_not_critical_when_other_employee_has_events():
    service = EusrrAttendanceService(_df([
        ("100", "2026-04-20T09:00:00"),
        ("100", "2026-04-20T18:00:00"),
        ("200", "2026-04-21T09:00:00"),
        ("200", "2026-04-21T18:00:00"),
        ("100", "2026-04-22T09:00:00"),
        ("100", "2026-04-22T18:00:00"),
    ]))
    request = _request(period_start="2026-04-20", period_end="2026-04-22")

    records = {record.date: record for record in service.analyze(request).records}
    absence = records[date(2026, 4, 21)]

    assert "Отсутствие" in absence.employee_issues
    assert not any(
        "критического отсутствия" in issue
        for issue in absence.technical_issues
    )


def test_period_start_after_period_end_is_rejected():
    with pytest.raises(ValueError):
        _request(period_start="2026-04-27", period_end="2026-04-20")


def test_response_to_dict_is_api_serializable_shape():
    response = EusrrAttendanceService(_df([])).analyze(_request(
        period_start="2026-04-20",
        period_end="2026-04-20",
    ))

    payload = response.to_dict()

    assert payload["employee_id"] == "100"
    assert payload["period_start"] == "2026-04-20"
    assert payload["records"][0]["date"] == "2026-04-20"
    assert payload["records"][0]["employee_id"] == "100"
    assert payload["records"][0]["is_absent"] is True
