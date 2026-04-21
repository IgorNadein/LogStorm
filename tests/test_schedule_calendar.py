from datetime import date, time

import pytest

from core.models import WorkSchedule


def _schedule(overrides=None):
    return WorkSchedule.from_preferences({
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
        "date_overrides": overrides or [],
    })


def test_regular_workday_from_weekdays():
    schedule = _schedule()

    settings = schedule.get_day_settings(date(2026, 4, 20))

    assert settings["is_workday"] is True
    assert settings["start_time"] == time(9, 0)
    assert settings["end_time"] == time(18, 0)
    assert settings["expected_hours"] == 9


def test_regular_weekend_from_weekdays():
    schedule = _schedule()

    settings = schedule.get_day_settings(date(2026, 4, 25))

    assert settings["is_workday"] is False


def test_weekday_can_be_overridden_as_day_off():
    schedule = _schedule([
        {
            "date": "2026-04-20",
            "is_workday": False,
            "reason": "holiday",
        }
    ])

    assert schedule.get_day_settings(date(2026, 4, 20))["is_workday"] is False


def test_weekend_can_be_overridden_as_workday():
    schedule = _schedule([
        {
            "date": "2026-04-25",
            "is_workday": True,
            "reason": "transferred_workday",
        }
    ])

    assert schedule.get_day_settings(date(2026, 4, 25))["is_workday"] is True


def test_override_can_define_shortened_day():
    schedule = _schedule([
        {
            "date": "2026-04-24",
            "is_workday": True,
            "reason": "short_day",
            "start_time": "09:00",
            "end_time": "16:00",
            "expected_hours": 7,
        }
    ])

    settings = schedule.get_day_settings(date(2026, 4, 24))

    assert settings["is_workday"] is True
    assert settings["start_time"] == time(9, 0)
    assert settings["end_time"] == time(16, 0)
    assert settings["expected_hours"] == 7


def test_empty_overrides_keep_legacy_behavior():
    schedule = _schedule([])

    assert schedule.is_workday("Monday", date(2026, 4, 20)) is True
    assert schedule.is_workday("Saturday", date(2026, 4, 25)) is False


def test_invalid_override_date_is_rejected():
    with pytest.raises(ValueError):
        _schedule([{"date": "24.04.2026", "is_workday": True}])
