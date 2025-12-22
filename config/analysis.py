"""
Analysis Configuration - настройки анализа посещаемости
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class ScheduleConfig:
    """Конфигурация рабочего графика"""
    workdays: List[str] = field(default_factory=lambda: [
        'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'
    ])
    start_time: str = '09:00'
    end_time: str = '18:00'
    work_hours: int = 9


@dataclass
class AnalysisConfig:
    """Настройки анализа посещаемости"""
    
    # Рабочий график по умолчанию
    default_work_hours: int = 9
    default_start_time: str = '08:00'
    default_end_time: str = '17:00'
    default_schedule: ScheduleConfig = field(
        default_factory=ScheduleConfig
    )
    
    # Пороги для анализа
    overtime_threshold: int = 10  # Переработка: более N часов в день
    late_threshold_minutes: int = 15  # Опоздание если > N минут
    critical_late_minutes: int = 180  # Критическое опоздание (3+ часа)
    critical_underwork_hours: int = 7  # Критическая недоработка
    critical_underwork_diff: int = 2  # На N+ часов меньше нормы
    
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
