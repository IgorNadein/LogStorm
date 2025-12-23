#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модель графика работы пользователя
"""

from dataclasses import dataclass
from datetime import time
from typing import List


@dataclass
class WorkSchedule:
    """График работы пользователя"""
    
    start_time: time
    end_time: time
    workdays: List[str]  # ['Monday', 'Tuesday', ...]
    expected_hours: float
    
    def is_workday(self, weekday: str) -> bool:
        """Проверка, является ли день рабочим для этого графика"""
        return weekday in self.workdays
    
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
        from datetime import datetime, timedelta
        
        # Время начала
        start_str = user_prefs.get('start_time', default_start)
        start_time = datetime.strptime(start_str, '%H:%M').time()
        
        # Продолжительность рабочего дня
        work_hours = user_prefs.get('work_hours', default_hours)
        
        # Время окончания = начало + work_hours
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
            expected_hours=work_hours
        )
