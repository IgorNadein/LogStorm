#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Валидатор массовых и критических отсутствий
"""

import pandas as pd
from datetime import date
from typing import Set
from models import WorkSchedule
from config import MASS_ABSENCE_THRESHOLD, CRITICAL_ABSENCE_THRESHOLD


class AbsenceValidator:
    """
    Валидация массовых и критических отсутствий
    
    Определяет дни, когда:
    - Массовое отсутствие: >90% работников отсутствуют (в рабочие дни)
    - Критическое отсутствие: 100% отсутствуют (включая выходные)
    """
    
    def __init__(self, df: pd.DataFrame, prefs: dict):
        """
        Args:
            df: DataFrame с логами посещаемости
            prefs: Словарь с настройками пользователей
        """
        self.df = df
        self.prefs = prefs
    
    def detect_mass_absence_days(self) -> Set[date]:
        """
        Определение дней с массовым отсутствием работников (>90%)
        
        Проверяет только рабочие дни. Если отсутствует >90% работников,
        которые должны были работать - это массовое отсутствие.
        
        Returns:
            Множество дат с массовым отсутствием
        """
        mass_absence_dates = set()
        if self.df.empty:
            return mass_absence_dates
        
        # Диапазон дат для проверки
        min_date = self.df['date'].min()
        max_date = self.df['date'].max()
        all_dates = pd.date_range(start=min_date, end=max_date, freq='D').date
        
        for curr_date in all_dates:
            # Определяем день недели
            weekday = pd.Timestamp(curr_date).day_name()
            
            # Подсчитываем, сколько пользователей должны работать
            users_should_work = 0
            for user_name in self.prefs.keys():
                user_prefs = self.prefs[user_name]
                schedule = WorkSchedule.from_preferences(user_prefs)
                if schedule.is_workday(weekday):
                    users_should_work += 1
            
            # Если это рабочий день хотя бы для кого-то
            if users_should_work > 0:
                # Подсчитываем присутствующих
                users_present = len(
                    self.df[self.df['date'] == curr_date]['name'].unique()
                )
                
                # Процент отсутствующих
                absence_rate = 1 - (users_present / users_should_work)
                
                # Если отсутствует более MASS_ABSENCE_THRESHOLD (90%)
                if absence_rate > MASS_ABSENCE_THRESHOLD:
                    mass_absence_dates.add(curr_date)
                    print(
                        f"  ! Массовое отсутствие {curr_date}: "
                        f"{users_present}/{users_should_work} "
                        f"({absence_rate*100:.1f}% отсутствуют)"
                    )
        
        return mass_absence_dates
    
    def detect_critical_absence_days(self) -> Set[date]:
        """
        Определение дней с критическим отсутствием (100%)
        
        Проверяет все дни (включая выходные). Если никто не пришёл -
        это критическое отсутствие (возможно, выходной или сбой системы).
        
        Returns:
            Множество дат с критическим отсутствием
        """
        critical_absence_dates = set()
        if self.df.empty:
            return critical_absence_dates
        
        # Диапазон дат для проверки
        min_date = self.df['date'].min()
        max_date = self.df['date'].max()
        all_dates = pd.date_range(start=min_date, end=max_date, freq='D').date
        
        total_users = len(self.prefs.keys()) or self.df['name'].nunique()
        if total_users == 0:
            return critical_absence_dates
        
        for curr_date in all_dates:
            # Подсчитываем присутствующих
            users_present = len(
                self.df[self.df['date'] == curr_date]['name'].unique()
            )
            
            # Если никто не пришел (100% отсутствие)
            if users_present == 0:
                critical_absence_dates.add(curr_date)
                print(
                    f"  ! Критическое отсутствие {curr_date}: "
                    f"0/{total_users} (100% отсутствуют)"
                )
        
        return critical_absence_dates
