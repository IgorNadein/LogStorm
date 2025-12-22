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
                        default_end: str = '17:00', default_hours: float = 9.0):
        """
        Создание графика из настроек пользователя
        
        Args:
            user_prefs: Словарь с настройками пользователя из person_prefs.json
            default_start: Время начала по умолчанию
            default_end: Время окончания по умолчанию
            default_hours: Продолжительность рабочего дня по умолчанию
        """
        from datetime import datetime, timedelta
        
        # Время начала
        start_str = user_prefs.get('start_time', default_start)
        start_time = datetime.strptime(start_str, '%H:%M').time()
        
        # Время окончания
        if 'end_time' in user_prefs:
            end_str = user_prefs['end_time']
            end_time = datetime.strptime(end_str, '%H:%M').time()
        else:
            # Рассчитываем конец как начало + N часов
            start_datetime = datetime.combine(datetime.today(), start_time)
            end_datetime = start_datetime + timedelta(hours=default_hours)
            end_time = end_datetime.time()
        
        # Рабочие дни
        workdays = user_prefs.get('workdays', 
                                  ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'])
        
        # Ожидаемая продолжительность
        start_dt = datetime.combine(datetime.today(), start_time)
        end_dt = datetime.combine(datetime.today(), end_time)
        expected_hours = (end_dt - start_dt).total_seconds() / 3600
        
        return cls(
            start_time=start_time,
            end_time=end_time,
            workdays=workdays,
            expected_hours=expected_hours
        )
