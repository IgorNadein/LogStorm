#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модель графика работы пользователя
"""

from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ScheduleDateOverride:
    """Исключение рабочего календаря для конкретной даты."""

    date: date
    is_workday: bool
    reason: str = ''
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    expected_hours: Optional[float] = None


@dataclass
class WorkSchedule:
    """График работы пользователя"""
    
    start_time: time
    end_time: time
    workdays: List[str]  # ['Monday', 'Tuesday', ...]
    expected_hours: float
    date_overrides: Dict[date, ScheduleDateOverride] = field(default_factory=dict)
    
    def is_workday(self, weekday: str, curr_date: Optional[date] = None) -> bool:
        """Проверка, является ли день рабочим для этого графика"""
        if curr_date in self.date_overrides:
            return self.date_overrides[curr_date].is_workday
        return weekday in self.workdays

    def get_day_settings(self, curr_date: date) -> dict:
        """
        Получить параметры графика для конкретной даты.

        date_overrides имеют приоритет над недельным графиком.
        """
        weekday = datetime.combine(curr_date, time()).strftime('%A')
        override = self.date_overrides.get(curr_date)
        return {
            'is_workday': (
                override.is_workday if override else weekday in self.workdays
            ),
            'start_time': (
                override.start_time if override and override.start_time
                else self.start_time
            ),
            'end_time': (
                override.end_time if override and override.end_time
                else self.end_time
            ),
            'expected_hours': (
                override.expected_hours
                if override and override.expected_hours is not None
                else self.expected_hours
            ),
        }
    
    @classmethod
    def from_preferences(cls, user_prefs: dict, default_start: str = '08:00',
                        default_hours: float = 9.0):
        """
        Создание графика из настроек пользователя
        
        Args:
            user_prefs: Словарь с настройками пользователя
            default_start: Время начала по умолчанию
            default_hours: Продолжительность рабочего дня по умолчанию
            
        Логика:
            - start_time: из настроек или default_start
            - work_hours: из настроек или default_hours
            - end_time: рассчитывается как start_time + work_hours
            - workdays: из настроек или Пн-Пт
        """
        from datetime import timedelta
        
        # Время начала
        start_str = user_prefs.get('start_time', default_start)
        start_time = cls._parse_time(start_str)
        
        # Продолжительность рабочего дня
        work_hours = user_prefs.get(
            'work_hours',
            user_prefs.get('expected_hours', default_hours)
        )
        
        # Время окончания: явное значение или начало + work_hours
        end_str = user_prefs.get('end_time')
        if end_str:
            end_time = cls._parse_time(end_str)
        else:
            start_datetime = datetime.combine(datetime.today(), start_time)
            end_datetime = start_datetime + timedelta(hours=work_hours)
            end_time = end_datetime.time()
        
        # Рабочие дни
        workdays = user_prefs.get('workdays', [
            'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'
        ])
        
        return cls(
            start_time=start_time,
            end_time=end_time,
            workdays=workdays,
            expected_hours=work_hours,
            date_overrides=cls._parse_date_overrides(
                user_prefs.get('date_overrides', [])
            )
        )

    @staticmethod
    def _parse_time(value: Any) -> time:
        if isinstance(value, time):
            return value
        return datetime.strptime(str(value), '%H:%M').time()

    @classmethod
    def _parse_date_overrides(
        cls, raw_overrides: Any
    ) -> Dict[date, ScheduleDateOverride]:
        if not raw_overrides:
            return {}

        if isinstance(raw_overrides, dict):
            iterable = [
                {'date': key, **value}
                for key, value in raw_overrides.items()
            ]
        else:
            iterable = raw_overrides

        overrides = {}
        for item in iterable:
            override_date = cls._parse_date(item['date'])
            overrides[override_date] = ScheduleDateOverride(
                date=override_date,
                is_workday=bool(item['is_workday']),
                reason=item.get('reason', ''),
                start_time=(
                    cls._parse_time(item['start_time'])
                    if item.get('start_time') else None
                ),
                end_time=(
                    cls._parse_time(item['end_time'])
                    if item.get('end_time') else None
                ),
                expected_hours=item.get('expected_hours'),
            )
        return overrides

    @staticmethod
    def _parse_date(value: Any) -> date:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return datetime.strptime(str(value), '%Y-%m-%d').date()
