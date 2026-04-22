#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Утилиты для работы с датами
"""

import pandas as pd
from datetime import date
from typing import List
from core.settings import DAYS_RU


class DateUtils:
    """Утилиты для работы с датами"""
    
    @staticmethod
    def get_weekday_ru(curr_date: date) -> str:
        """
        Русское название дня недели
        
        Args:
            curr_date: Дата
            
        Returns:
            Русское название дня недели
        """
        weekday_en = pd.Timestamp(curr_date).day_name()
        return DAYS_RU.get(weekday_en, weekday_en)
    
    @staticmethod
    def get_date_range(start: date, end: date) -> List[date]:
        """
        Диапазон дат
        
        Args:
            start: Начальная дата
            end: Конечная дата
            
        Returns:
            Список всех дат в диапазоне
        """
        return pd.date_range(start=start, end=end, freq='D').date
