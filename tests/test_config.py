"""Tests for central LogStorm settings."""

import pytest

from core.settings import (
    DEFAULT_WORK_HOURS,
    LATE_THRESHOLD_MINUTES,
    OVERTIME_THRESHOLD,
    NIGHT_HOUR_START,
    NIGHT_HOUR_END,
    DEFAULT_SCHEDULE,
    DAYS_RU,
    MONTHS_RU
)


class TestSettingsConstants:
    """Core settings should expose the project defaults."""

    def test_late_threshold_exists(self):
        """Проверка что LATE_THRESHOLD_MINUTES доступна"""
        assert LATE_THRESHOLD_MINUTES == 5
    
    def test_overtime_threshold_exists(self):
        """Проверка что OVERTIME_THRESHOLD доступна"""
        assert OVERTIME_THRESHOLD == 10
    
    def test_night_hours_exist(self):
        """Проверка ночных часов"""
        assert NIGHT_HOUR_START == 23
        assert NIGHT_HOUR_END == 3
    
    def test_default_schedule_is_dict(self):
        """Проверка что DEFAULT_SCHEDULE - словарь"""
        assert isinstance(DEFAULT_SCHEDULE, dict)
        assert 'workdays' in DEFAULT_SCHEDULE
        assert 'start_time' in DEFAULT_SCHEDULE
        assert DEFAULT_SCHEDULE['expected_hours'] == DEFAULT_WORK_HOURS
        assert DEFAULT_SCHEDULE['work_hours'] == DEFAULT_WORK_HOURS
    
    def test_days_ru_has_all_days(self):
        """Проверка что все дни переведены"""
        assert len(DAYS_RU) == 7
        assert 'Monday' in DAYS_RU
        assert DAYS_RU['Monday'] == 'Понедельник'
    
    def test_months_ru_has_all_months(self):
        """Проверка что все месяцы переведены"""
        assert len(MONTHS_RU) == 12
        assert 1 in MONTHS_RU
        assert MONTHS_RU[1] == 'Январь'

class TestAnalysisSettings:
    """Tests for analysis settings."""
    
    def test_default_schedule(self):
        """Проверка расписания по умолчанию"""
        assert DEFAULT_SCHEDULE["work_hours"] == 9
        assert len(DEFAULT_SCHEDULE["workdays"]) == 5
        assert 'Monday' in DEFAULT_SCHEDULE["workdays"]
        assert 'Saturday' not in DEFAULT_SCHEDULE["workdays"]
    
    def test_thresholds_are_positive(self):
        """Проверка что все пороги положительные"""
        assert LATE_THRESHOLD_MINUTES > 0
        assert OVERTIME_THRESHOLD > 0
    
    def test_night_hours_valid(self):
        """Проверка что ночные часы валидны"""
        assert 0 <= NIGHT_HOUR_START <= 23
        assert 0 <= NIGHT_HOUR_END <= 23


class TestFormattingSettings:
    """Tests for formatting settings."""
    
    def test_colors_are_hex(self):
        """Проверка что цвета в hex формате"""
        from core.settings import HEADER_COLOR

        assert len(HEADER_COLOR) == 6
        assert all(c in '0123456789ABCDEF' for c in HEADER_COLOR.upper())
    
    def test_sheet_names_not_empty(self):
        """Проверка что названия листов заполнены"""
        from core.settings import SHEET_MAIN_REPORT, SHEET_SUSPICIOUS

        assert len(SHEET_MAIN_REPORT) > 0
        assert len(SHEET_SUSPICIOUS) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
