#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Валидатор временных данных
"""

import pandas as pd

# Импортируем пороговые значения из config
# Эти значения можно настроить в config.py
from config import (
    CRITICAL_LATE_MINUTES,
    CRITICAL_UNDERWORK_HOURS,
    CRITICAL_UNDERWORK_DIFF,
    NIGHT_HOUR_START,
    NIGHT_HOUR_END
)


class TimeValidator:
    """Валидация временных данных и аномалий"""
    
    @staticmethod
    def filter_night_entries(entries: pd.DataFrame) -> pd.DataFrame:
        """
        Фильтрует ночные записи (23:00-04:00)
        
        Args:
            entries: DataFrame с записями, должен содержать колонку 'timestamp'
            
        Returns:
            DataFrame только с дневными записями (04:00-23:00)
        """
        return entries[
            (entries['timestamp'].dt.hour >= NIGHT_HOUR_END) &
            (entries['timestamp'].dt.hour < NIGHT_HOUR_START)
        ]
    
    @staticmethod
    def has_night_activity(arrival_time, departure_time) -> bool:
        """
        Проверяет, является ли время прихода или ухода ночным (23:00-04:00)
        
        Args:
            arrival_time: Время прихода (time объект или None)
            departure_time: Время ухода (time объект или None)
            
        Returns:
            True если приход или уход в ночное время
        """
        def is_night_hour(time_obj) -> bool:
            if time_obj is None:
                return False
            hour = time_obj.hour
            # Ночь: с 23:00 до 04:00
            return hour >= NIGHT_HOUR_START or hour < NIGHT_HOUR_END
        
        return is_night_hour(arrival_time) or is_night_hour(departure_time)
    
    @staticmethod
    def is_extreme_late(late_minutes: int) -> bool:
        """
        Проверяет, является ли опоздание экстремальным (>3 часа)
        
        Args:
            late_minutes: Количество минут опоздания
            
        Returns:
            True если опоздание >= CRITICAL_LATE_MINUTES (180 минут)
        """
        return late_minutes >= CRITICAL_LATE_MINUTES

    @staticmethod
    def is_critical_underwork(work_hours: float,
                              expected_hours: float) -> bool:
        """
        Проверяет, является ли недоработка критической

        Критическая недоработка:
        1. Отработано менее 7 часов (<CRITICAL_UNDERWORK_HOURS)
        2. На 2+ часа меньше нормы (>=CRITICAL_UNDERWORK_DIFF)

        Args:
            work_hours: Фактически отработанные часы
            expected_hours: Ожидаемые часы по графику

        Returns:
            True если недоработка критическая
        """
        hours_diff = expected_hours - work_hours
        return (
            work_hours < CRITICAL_UNDERWORK_HOURS or
            hours_diff >= CRITICAL_UNDERWORK_DIFF
        )
