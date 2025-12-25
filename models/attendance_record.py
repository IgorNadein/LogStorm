#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модель записи посещаемости за один день
"""

from dataclasses import dataclass, field
from datetime import date, time
from typing import Optional, List


@dataclass
class AttendanceRecord:
    """
    Одна запись посещаемости пользователя за день
    
    Содержит всю информацию о присутствии пользователя, его статусах
    (опоздания, переработки), а также выявленных проблемах.
    """
    
    # === Базовая информация ===
    date: date
    user_name: str  # ID пользователя
    display_name: str  # Отображаемое имя
    
    # === Временные данные ===
    arrival_time: Optional[time]
    departure_time: Optional[time]
    work_hours: float
    appearances: int  # Количество появлений в логах (без ночных записей)
    
    # === Контекст ===
    weekday: str  # 'Monday', 'Tuesday', ...
    is_workday: bool
    schedule_start: time
    schedule_end: time
    expected_hours: float
    
    # Пути к фото (для гиперссылок в Excel)
    arrival_photo_path: Optional[str] = None
    departure_photo_path: Optional[str] = None
    
    # === Статусы (заполняются анализаторами) ===
    is_late: bool = False
    late_minutes: int = 0
    
    is_early_leave: bool = False
    early_leave_minutes: int = 0
    
    is_underwork: bool = False
    is_overtime: bool = False
    
    # === Проблемы ===
    technical_issues: List[str] = field(default_factory=list)
    employee_issues: List[str] = field(default_factory=list)
    
    # === Свойства для удобства ===
    
    @property
    def has_technical_issues(self) -> bool:
        """Есть ли технические сбои"""
        return len(self.technical_issues) > 0
    
    @property
    def is_valid_record(self) -> bool:
        """Валидная запись = нет технических сбоев"""
        return not self.has_technical_issues
    
    @property
    def has_employee_issues(self) -> bool:
        """Есть ли проблемы сотрудника"""
        return len(self.employee_issues) > 0
    
    @property
    def technical_issues_text(self) -> str:
        """Текстовое описание технических проблем"""
        return ', '.join(self.technical_issues) if self.technical_issues else 'Нет'
    
    @property
    def employee_issues_text(self) -> str:
        """Текстовое описание проблем сотрудника"""
        return ', '.join(self.employee_issues) if self.employee_issues else 'Нет'
    
    def to_dict(self) -> dict:
        """Конвертация в словарь для DataFrame"""
        from config import DAYS_RU
        
        return {
            'День недели': DAYS_RU.get(self.weekday, self.weekday),
            'Дата': self.date,
            'Имя': self.display_name,
            'ID': self.user_name,
            'Приход': self.arrival_time.strftime('%H:%M:%S') if self.arrival_time else '-',
            'Уход': self.departure_time.strftime('%H:%M:%S') if self.departure_time else '-',
            'Рабочих часов': round(self.work_hours, 2),
            'Опоздание': 'Да' if self.is_late else 'Нет',
            'Опоздание (мин)': self.late_minutes,
            'Ранний уход': 'Да' if self.is_early_leave else 'Нет',
            'Недоработка (мин)': self.early_leave_minutes,
            'Недоработка часов': 'Да' if self.is_underwork else 'Нет',
            'Переработка': 'Да' if self.is_overtime else 'Нет',
            'Появлений': self.appearances,
            'Технический сбой': self.technical_issues_text,
            'Проблемы сотрудника': self.employee_issues_text,
            'График начало': self.schedule_start.strftime('%H:%M'),
            'График конец': self.schedule_end.strftime('%H:%M'),
            'Рабочий день': 'Да' if self.is_workday else 'Нет'
        }
