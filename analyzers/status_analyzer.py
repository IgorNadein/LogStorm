#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Анализатор статусов сотрудника
"""

from datetime import datetime
from typing import Tuple, List
from models import AttendanceRecord
from config import (
    OVERTIME_THRESHOLD,
    LATE_THRESHOLD_MINUTES,
    CRITICAL_LATE_MINUTES,
    CRITICAL_UNDERWORK_HOURS
)


class StatusAnalyzer:
    """
    Определение статусов сотрудника
    
    Анализирует:
    - Опоздания
    - Ранние уходы
    - Недоработки
    - Переработки
    - Проблемы сотрудника (только если НЕТ технических сбоев)
    """
    
    @staticmethod
    def analyze_late(record: AttendanceRecord) -> Tuple[bool, int]:
        """
        Проверка опоздания
        
        Args:
            record: Запись посещаемости
        
        Returns:
            (is_late: bool, late_minutes: int)
        """
        if not record.is_workday or not record.arrival_time:
            return False, 0
        
        if record.arrival_time > record.schedule_start:
            late_delta = (
                datetime.combine(record.date, record.arrival_time) -
                datetime.combine(record.date, record.schedule_start)
            )
            late_minutes = int(late_delta.total_seconds() / 60)
            
            # Опоздание учитывается только >LATE_THRESHOLD_MINUTES (15 минут)
            if late_minutes > LATE_THRESHOLD_MINUTES:
                return True, late_minutes
        
        return False, 0
    
    @staticmethod
    def analyze_early_leave(record: AttendanceRecord) -> Tuple[bool, int]:
        """
        Проверка раннего ухода
        
        Args:
            record: Запись посещаемости
        
        Returns:
            (is_early_leave: bool, early_leave_minutes: int)
        """
        if not record.is_workday or not record.departure_time:
            return False, 0
        
        if record.departure_time < record.schedule_end:
            underwork_delta = (
                datetime.combine(record.date, record.schedule_end) -
                datetime.combine(record.date, record.departure_time)
            )
            underwork_minutes = int(underwork_delta.total_seconds() / 60)
            return True, underwork_minutes
        
        return False, 0
    
    @staticmethod
    def analyze_underwork(record: AttendanceRecord) -> bool:
        """
        Проверка недоработки по часам
        
        Args:
            record: Запись посещаемости
        
        Returns:
            True если отработал меньше положенного (только в рабочие дни)
        """
        if not record.is_workday:
            return False
        return record.work_hours < record.expected_hours
    
    @staticmethod
    def analyze_overtime(record: AttendanceRecord) -> bool:
        """
        Проверка переработки
        
        Логика:
        - В рабочий день: переработка если >OVERTIME_THRESHOLD (10) часов
        - В выходной день: переработка если есть хоть одна запись
        
        Args:
            record: Запись посещаемости
        
        Returns:
            True если есть переработка
        """
        if record.is_workday:
            # В рабочий день - если >10 часов
            return record.work_hours > OVERTIME_THRESHOLD
        else:
            # В выходной - любая работа = переработка
            return record.appearances > 0
    
    @staticmethod
    def get_employee_issues(record: AttendanceRecord) -> List[str]:
        """
        Определение проблем сотрудника
        
        ВАЖНО: Проблемы сотрудника учитываются ТОЛЬКО если НЕТ технических сбоев!
        
        Args:
            record: Запись посещаемости (должна быть уже заполнена статусами)
        
        Returns:
            Список проблем сотрудника
        """
        # Если есть технические сбои - проблемы сотрудника не учитываются
        if record.has_technical_issues:
            return []
        
        issues = []
        
        # 1. Отсутствие в рабочий день (без технических причин)
        if record.appearances == 0 and record.is_workday:
            issues.append("Отсутствие")
            return issues  # Остальное не проверяем
        
        # 2. Опоздание (от 15 минут до 3 часов)
        if (record.is_late and 
            LATE_THRESHOLD_MINUTES < record.late_minutes < CRITICAL_LATE_MINUTES):
            issues.append(f"Опоздание {record.late_minutes} мин")
        
        # 3. Недоработка (не критическая: >= 3 часов, но < нормы)
        hours_diff = record.expected_hours - record.work_hours
        is_not_critical = record.work_hours >= CRITICAL_UNDERWORK_HOURS
        if record.is_underwork and is_not_critical:
            issues.append(f"Недоработка {hours_diff:.1f}ч")
        
        return issues
    
    @staticmethod
    def should_count_in_summary(record: AttendanceRecord,
                                status_type: str) -> bool:
        """
        Определяет, нужно ли учитывать запись в итоговой статистике
        
        ВАЖНО: Это исправляет баг с подсчётом итогов!
        Опоздания/переработки должны считаться ТОЛЬКО по валидным записям.
        
        Args:
            record: Запись посещаемости
            status_type: Тип статуса ('late', 'overtime', 'early_leave', 'hours')
        
        Returns:
            True если запись должна учитываться в итогах
        """
        # Опоздания, переработки, ранние уходы - только валидные записи
        if status_type in ['late', 'overtime', 'early_leave']:
            return record.is_valid_record
        
        # Отработанные часы - только валидные записи
        if status_type == 'hours':
            return record.is_valid_record
        
        # Для других случаев (например, подсчёт всех дней) - учитываем все
        return True
