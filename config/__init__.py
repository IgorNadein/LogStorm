"""
LogStorm Configuration Package

Централизованное управление конфигурацией приложения.

Использование (новый способ):
    from config import config_manager
    threshold = config_manager.analysis.late_threshold_minutes

Использование (обратная совместимость):
    from config import LATE_THRESHOLD_MINUTES
"""

from .analysis import AnalysisConfig, ScheduleConfig, analysis_config
from .formatting import FormattingConfig, formatting_config
from .paths import PathsConfig, paths_config
from .localization import LocalizationConfig, localization_config
from .ai import AIConfig, ai_config


class ConfigManager:
    """
    Централизованный менеджер конфигурации.
    
    Примеры использования:
        config_manager.analysis.late_threshold_minutes
        config_manager.formatting.header_color
        config_manager.paths.logs_file
        config_manager.localization.days_ru['Monday']
    """
    
    def __init__(self):
        self.analysis = analysis_config
        self.formatting = formatting_config
        self.paths = paths_config
        self.localization = localization_config
        self.ai = ai_config
    
    def reload(self):
        """Перезагрузить конфигурацию из файла (для будущего использования)"""
        pass  # TODO: реализовать загрузку из JSON файла


# Глобальный менеджер конфигурации
config_manager = ConfigManager()


# ============================================================
# ОБРАТНАЯ СОВМЕСТИМОСТЬ
# Эти константы сохранены для совместимости со старым кодом.
# В новом коде рекомендуется использовать config_manager.
# ============================================================

# === ПУТИ К ФАЙЛАМ ===
LOGS_FILE = paths_config.logs_file
PERSON_MAPPING_FILE = paths_config.person_mapping_file
OUTPUT_EXCEL_FILE = paths_config.output_excel_file
OUTPUT_AI_SUMMARY_FILE = paths_config.output_ai_summary_file

# === РАБОЧИЙ ГРАФИК ===
DEFAULT_WORK_HOURS = analysis_config.default_work_hours
DEFAULT_START_TIME = analysis_config.default_start_time
DEFAULT_END_TIME = analysis_config.default_end_time

DEFAULT_SCHEDULE = {
    'workdays': analysis_config.default_schedule.workdays,
    'start_time': analysis_config.default_schedule.start_time,
    'end_time': analysis_config.default_schedule.end_time,
    'work_hours': analysis_config.default_schedule.work_hours
}

# === ПОРОГИ ДЛЯ АНАЛИЗА ===
OVERTIME_THRESHOLD = analysis_config.overtime_threshold
LATE_THRESHOLD_MINUTES = analysis_config.late_threshold_minutes
CRITICAL_LATE_MINUTES = analysis_config.critical_late_minutes
CRITICAL_UNDERWORK_HOURS = analysis_config.critical_underwork_hours
CRITICAL_UNDERWORK_DIFF = analysis_config.critical_underwork_diff
MASS_ABSENCE_THRESHOLD = analysis_config.mass_absence_threshold
CRITICAL_ABSENCE_THRESHOLD = analysis_config.critical_absence_threshold

# === ВРЕМЕННЫЕ ДИАПАЗОНЫ ===
NIGHT_HOUR_START = analysis_config.night_hour_start
NIGHT_HOUR_END = analysis_config.night_hour_end

# === EXCEL ФОРМАТИРОВАНИЕ ===
HEADER_COLOR = formatting_config.header_color
SUMMARY_HEADER_COLOR = formatting_config.summary_header_color
LATE_BG_COLOR = formatting_config.late_bg_color
OVERTIME_BG_COLOR = formatting_config.overtime_bg_color
SUSPICIOUS_BG_COLOR = formatting_config.suspicious_bg_color
LATE_CELL_COLOR = formatting_config.late_cell_color
UNDERWORK_CELL_COLOR = formatting_config.underwork_cell_color
OVERTIME_CELL_COLOR = formatting_config.overtime_cell_color
SUSPICIOUS_CELL_COLOR = formatting_config.suspicious_cell_color
TECHNICAL_FILL_COLOR = formatting_config.technical_fill_color

# === НАЗВАНИЯ ЛИСТОВ EXCEL ===
SHEET_MAIN_REPORT = formatting_config.sheet_main_report
SHEET_SUSPICIOUS = formatting_config.sheet_suspicious
SHEET_MONTH_PREFIX = formatting_config.sheet_month_prefix

# === СТАТИСТИКА ===
TOP_N_USERS = analysis_config.top_n_users
MAX_SUSPICIOUS_DETAILS = analysis_config.max_suspicious_details

# === AI АНАЛИЗ ===
GIGACHAT_SCOPE = ai_config.gigachat_scope
AI_PROMPT_SENTENCES = ai_config.ai_prompt_sentences

# === НАЗВАНИЯ ДЛЯ ОТЧЕТОВ ===
DAYS_RU = localization_config.days_ru
DAYS_ORDER = localization_config.days_order
MONTHS_RU = localization_config.months_ru


__all__ = [
    # Новый API
    'config_manager',
    'ConfigManager',
    'AnalysisConfig',
    'FormattingConfig',
    'PathsConfig',
    'LocalizationConfig',
    'AIConfig',
    'ScheduleConfig',
    
    # Обратная совместимость - пути
    'LOGS_FILE',
    'PERSON_MAPPING_FILE',
    'OUTPUT_EXCEL_FILE',
    'OUTPUT_AI_SUMMARY_FILE',
    
    # Обратная совместимость - график
    'DEFAULT_WORK_HOURS',
    'DEFAULT_START_TIME',
    'DEFAULT_END_TIME',
    'DEFAULT_SCHEDULE',
    
    # Обратная совместимость - пороги
    'OVERTIME_THRESHOLD',
    'LATE_THRESHOLD_MINUTES',
    'CRITICAL_LATE_MINUTES',
    'CRITICAL_UNDERWORK_HOURS',
    'CRITICAL_UNDERWORK_DIFF',
    'MASS_ABSENCE_THRESHOLD',
    'CRITICAL_ABSENCE_THRESHOLD',
    
    # Обратная совместимость - время
    'NIGHT_HOUR_START',
    'NIGHT_HOUR_END',
    
    # Обратная совместимость - Excel
    'HEADER_COLOR',
    'SUMMARY_HEADER_COLOR',
    'LATE_BG_COLOR',
    'OVERTIME_BG_COLOR',
    'SUSPICIOUS_BG_COLOR',
    'LATE_CELL_COLOR',
    'UNDERWORK_CELL_COLOR',
    'OVERTIME_CELL_COLOR',
    'SUSPICIOUS_CELL_COLOR',
    'TECHNICAL_FILL_COLOR',
    'SHEET_MAIN_REPORT',
    'SHEET_SUSPICIOUS',
    'SHEET_MONTH_PREFIX',
    
    # Обратная совместимость - статистика
    'TOP_N_USERS',
    'MAX_SUSPICIOUS_DETAILS',
    
    # Обратная совместимость - AI
    'GIGACHAT_SCOPE',
    'AI_PROMPT_SENTENCES',
    
    # Обратная совместимость - локализация
    'DAYS_RU',
    'DAYS_ORDER',
    'MONTHS_RU',
]
