"""
Analysis Configuration - настройки анализа посещаемости
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class ScheduleConfig:
    """Конфигурация рабочего графика по умолчанию (единственный источник)"""
    workdays: List[str] = field(default_factory=lambda: [
        'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'
    ])
    start_time: str = '08:00'
    end_time: str = '17:00'
    work_hours: int = 9


@dataclass
class AnalysisConfig:
    """Настройки анализа посещаемости"""
    
    # Рабочий график по умолчанию (ссылается на ScheduleConfig)
    default_schedule: ScheduleConfig = field(
        default_factory=ScheduleConfig
    )
    
    @property
    def default_work_hours(self) -> int:
        return self.default_schedule.work_hours
    
    @property
    def default_start_time(self) -> str:
        return self.default_schedule.start_time
    
    @property
    def default_end_time(self) -> str:
        return self.default_schedule.end_time
    
    # Пороги для анализа
    overtime_threshold: int = 10  # Переработка: более N часов в день
    late_threshold_minutes: int = 5  # Опоздание если > N минут
    critical_late_minutes: int = 180  # Критическое опоздание (3+ часа)
    critical_underwork_hours: int = 3  # Критическая недоработка (< N ч)
    
    # Массовые отсутствия
    mass_absence_threshold: float = 0.8  # >80% отсутствуют
    critical_absence_threshold: float = 1.0  # 100% отсутствуют
    
    # Временные диапазоны
    night_hour_start: int = 23  # Начало ночного времени
    night_hour_end: int = 3  # Конец ночного времени
    
    # Статистика
    top_n_users: int = 5  # Количество в топах
    max_suspicious_details: int = 10  # Макс. подозрительных в консоли


# Глобальный экземпляр
analysis_config = AnalysisConfig()
