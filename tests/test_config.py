"""
Тесты для модуля конфигурации
"""

import pytest
from config import (
    config_manager,
    LATE_THRESHOLD_MINUTES,
    OVERTIME_THRESHOLD,
    NIGHT_HOUR_START,
    NIGHT_HOUR_END,
    DEFAULT_SCHEDULE,
    DAYS_RU,
    MONTHS_RU
)


class TestConfigBackwardCompatibility:
    """Тесты обратной совместимости"""
    
    def test_late_threshold_exists(self):
        """Проверка что LATE_THRESHOLD_MINUTES доступна"""
        assert LATE_THRESHOLD_MINUTES == 15
    
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


class TestConfigManager:
    """Тесты для ConfigManager"""
    
    def test_config_manager_exists(self):
        """Проверка что config_manager доступен"""
        assert config_manager is not None
    
    def test_analysis_config(self):
        """Проверка доступа к analysis config"""
        assert config_manager.analysis is not None
        assert config_manager.analysis.late_threshold_minutes == 15
        assert config_manager.analysis.overtime_threshold == 10
    
    def test_formatting_config(self):
        """Проверка доступа к formatting config"""
        assert config_manager.formatting is not None
        assert config_manager.formatting.header_color == "4472C4"
    
    def test_paths_config(self):
        """Проверка доступа к paths config"""
        assert config_manager.paths is not None
        assert 'person_mapping' in config_manager.paths.person_mapping_file
    
    def test_localization_config(self):
        """Проверка доступа к localization config"""
        assert config_manager.localization is not None
        assert len(config_manager.localization.days_ru) == 7
    
    def test_ai_config(self):
        """Проверка доступа к AI config"""
        assert config_manager.ai is not None
        assert config_manager.ai.gigachat_scope == 'GIGACHAT_API_PERS'


class TestAnalysisConfig:
    """Тесты для AnalysisConfig"""
    
    def test_default_schedule(self):
        """Проверка расписания по умолчанию"""
        schedule = config_manager.analysis.default_schedule
        assert schedule.work_hours == 9
        assert len(schedule.workdays) == 5
        assert 'Monday' in schedule.workdays
        assert 'Saturday' not in schedule.workdays
    
    def test_thresholds_are_positive(self):
        """Проверка что все пороги положительные"""
        analysis = config_manager.analysis
        assert analysis.late_threshold_minutes > 0
        assert analysis.overtime_threshold > 0
        assert analysis.critical_late_minutes > 0
        assert analysis.critical_underwork_hours > 0
    
    def test_night_hours_valid(self):
        """Проверка что ночные часы валидны"""
        analysis = config_manager.analysis
        assert 0 <= analysis.night_hour_start <= 23
        assert 0 <= analysis.night_hour_end <= 23


class TestFormattingConfig:
    """Тесты для FormattingConfig"""
    
    def test_colors_are_hex(self):
        """Проверка что цвета в hex формате"""
        formatting = config_manager.formatting
        assert len(formatting.header_color) == 6
        assert all(c in '0123456789ABCDEF' for c in formatting.header_color.upper())
    
    def test_sheet_names_not_empty(self):
        """Проверка что названия листов заполнены"""
        formatting = config_manager.formatting
        assert len(formatting.sheet_main_report) > 0
        assert len(formatting.sheet_suspicious) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
