from datetime import date, time

from analyzer import StatusAnalyzer, TechnicalIssueAnalyzer
from core.models import AttendanceRecord


def _record(
    *,
    curr_date=date(2026, 4, 20),
    weekday="Monday",
    is_workday=True,
    arrival=time(9, 0),
    departure=time(18, 0),
    work_hours=9,
    appearances=2,
    expected_hours=9,
):
    return AttendanceRecord(
        date=curr_date,
        user_name="100",
        display_name="Test User",
        arrival_time=arrival,
        departure_time=departure,
        work_hours=work_hours,
        appearances=appearances,
        weekday=weekday,
        is_workday=is_workday,
        schedule_start=time(9, 0),
        schedule_end=time(18, 0),
        expected_hours=expected_hours,
    )


def _analyze(record):
    record.is_late, record.late_minutes = StatusAnalyzer.analyze_late(record)
    record.is_early_leave, record.early_leave_minutes = (
        StatusAnalyzer.analyze_early_leave(record)
    )
    record.is_underwork = StatusAnalyzer.analyze_underwork(record)
    record.is_overtime = StatusAnalyzer.analyze_overtime(record)
    record.technical_issues = TechnicalIssueAnalyzer(set(), set()).analyze(
        record, None
    )
    record.employee_issues = StatusAnalyzer.get_employee_issues(record)
    return record


def test_on_time_workday_has_no_status_issues():
    record = _analyze(_record())

    assert record.is_late is False
    assert record.is_early_leave is False
    assert record.is_underwork is False
    assert record.is_overtime is False
    assert record.employee_issues == []


def test_late_workday_is_employee_issue():
    record = _analyze(_record(arrival=time(9, 30), work_hours=8.5))

    assert record.is_late is True
    assert record.late_minutes == 30
    assert "Опоздание 30 мин" in record.employee_issues


def test_early_leave_and_underwork_on_workday():
    record = _analyze(_record(departure=time(16, 0), work_hours=7))

    assert record.is_early_leave is True
    assert record.early_leave_minutes == 120
    assert record.is_underwork is True


def test_overtime_on_workday_requires_threshold():
    record = _analyze(_record(departure=time(20, 30), work_hours=11.5))

    assert record.is_overtime is True


def test_absence_on_workday_is_employee_issue():
    record = _analyze(_record(arrival=None, departure=None, work_hours=0, appearances=0))

    assert record.is_underwork is False
    assert "Отсутствие" in record.employee_issues


def test_absence_on_weekend_is_not_employee_issue():
    record = _analyze(_record(
        curr_date=date(2026, 4, 25),
        weekday="Saturday",
        is_workday=False,
        arrival=None,
        departure=None,
        work_hours=0,
        appearances=0,
    ))

    assert record.employee_issues == []
    assert record.technical_issues == []


def test_weekend_visit_is_overtime_without_late_or_underwork():
    record = _analyze(_record(
        curr_date=date(2026, 4, 25),
        weekday="Saturday",
        is_workday=False,
        arrival=time(12, 0),
        departure=time(14, 0),
        work_hours=2,
        appearances=2,
    ))

    assert record.is_late is False
    assert record.is_early_leave is False
    assert record.is_underwork is False
    assert record.is_overtime is True
    assert record.technical_issues == []


def test_transferred_workday_is_analyzed_as_workday():
    record = _analyze(_record(
        curr_date=date(2026, 4, 25),
        weekday="Saturday",
        is_workday=True,
        arrival=time(9, 30),
        departure=time(18, 0),
        work_hours=8.5,
    ))

    assert record.is_late is True
    assert record.is_underwork is True
