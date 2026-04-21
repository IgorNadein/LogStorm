#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сервис анализа посещаемости
"""

import pandas as pd
from datetime import datetime
from typing import List, Optional
from models import AttendanceRecord, WorkSchedule
from validators import AbsenceValidator
from analyzers import TechnicalIssueAnalyzer, StatusAnalyzer


class AttendanceService:
    """
    Основной сервис анализа посещаемости
    
    Координирует работу валидаторов и анализаторов для определения
    всех статусов пользователей за все дни.
    """
    
    def __init__(self, df: pd.DataFrame, prefs: dict):
        """
        Args:
            df: DataFrame с логами посещаемости
            prefs: Словарь с настройками пользователей
        """
        self.df = df
        self.prefs = prefs
        
        # Инициализация валидаторов
        print("Инициализация валидаторов...")
        absence_validator = AbsenceValidator(df, prefs)
        self.mass_absence_dates = absence_validator.detect_mass_absence_days()
        self.critical_absence_dates = (
            absence_validator.detect_critical_absence_days()
        )
        
        # Инициализация анализатора технических сбоев
        self.technical_analyzer = TechnicalIssueAnalyzer(
            self.mass_absence_dates,
            self.critical_absence_dates
        )
    
    def analyze_all(self, progress_callback=None) -> List[AttendanceRecord]:
        """
        Анализ всех пользователей за все дни
        
        Создаёт запись для каждой комбинации пользователь×дата,
        определяет все статусы и проблемы.
        
        Args:
            progress_callback: Опциональный callback для прогресса
                Сигнатура: callback(current, total, user_name)
        
        Returns:
            Список всех записей посещаемости
        """
        records = []
        
        # Диапазон дат
        min_date = self.df['date'].min()
        max_date = self.df['date'].max()
        all_dates = pd.date_range(start=min_date, end=max_date, freq='D').date
        
        # Все пользователи
        # Если prefs не задан - берём уникальных пользователей из логов
        if self.prefs:
            all_users = list(self.prefs.keys())
        else:
            all_users = self.df['name'].unique().tolist()
        
        # Группируем логи по пользователю и дате
        grouped = self.df.groupby(['name', 'date'])
        
        total_users = len(all_users)
        print(f"Анализ {total_users} пользователей за {len(all_dates)} дней...")
        
        # Анализируем каждую комбинацию пользователь×дата
        for user_idx, user_name in enumerate(all_users, 1):
            # Отправляем прогресс
            if progress_callback:
                display_name = self.prefs.get(
                    user_name, {}
                ).get('display_name', user_name)
                progress_callback(user_idx, total_users, display_name)
            
            for date in all_dates:
                record = self._analyze_user_day(user_name, date, grouped)
                records.append(record)
        
        print(f"Создано {len(records)} записей")
        return records
    
    def analyze_user_period(
        self,
        user_name: str,
        start_date,
        end_date,
        schedule: WorkSchedule,
        display_name: Optional[str] = None,
    ) -> List[AttendanceRecord]:
        """Анализ одного пользователя за заданный период и внешний график."""
        if start_date > end_date:
            raise ValueError("period_start must be less than or equal to period_end")

        grouped = self.df.groupby(['name', 'date'])
        dates = pd.date_range(start=start_date, end=end_date, freq='D').date
        return [
            self._analyze_user_day(
                user_name,
                curr_date,
                grouped,
                schedule=schedule,
                display_name=display_name,
            )
            for curr_date in dates
        ]

    def _analyze_user_day(
        self,
        user_name: str,
        date,
        grouped,
        schedule: Optional[WorkSchedule] = None,
        display_name: Optional[str] = None,
    ) -> AttendanceRecord:
        """
        Анализ одного пользователя за один день
        
        Args:
            user_name: ID пользователя
            date: Дата для анализа
            grouped: Сгруппированный DataFrame логов
            
        Returns:
            Заполненная запись AttendanceRecord
        """
        # 1. Создание базовой записи с временными данными
        record = self._create_base_record(
            user_name,
            date,
            grouped,
            schedule=schedule,
            display_name=display_name,
        )
        
        # 2. Определение базовых статусов (опоздание, ранний уход и т.д.)
        record.is_late, record.late_minutes = (
            StatusAnalyzer.analyze_late(record)
        )
        record.is_early_leave, record.early_leave_minutes = (
            StatusAnalyzer.analyze_early_leave(record)
        )
        record.is_underwork = StatusAnalyzer.analyze_underwork(record)
        record.is_overtime = StatusAnalyzer.analyze_overtime(record)
        
        # 3. Определение технических сбоев
        entries = None
        if (user_name, date) in grouped.groups:
            entries = grouped.get_group((user_name, date))
        
        record.technical_issues = self.technical_analyzer.analyze(
            record, entries
        )
        
        # 4. Определение проблем сотрудника (только если нет технических сбоев)
        record.employee_issues = StatusAnalyzer.get_employee_issues(record)
        
        return record
    
    def _create_base_record(
        self,
        user_name: str,
        date,
        grouped,
        schedule: Optional[WorkSchedule] = None,
        display_name: Optional[str] = None,
    ) -> AttendanceRecord:
        """
        Создание базовой записи с временными данными
        
        Извлекает время прихода/ухода, фильтрует ночные записи,
        рассчитывает рабочие часы.
        
        Args:
            user_name: ID пользователя
            date: Дата
            grouped: Сгруппированный DataFrame логов
            
        Returns:
            AttendanceRecord с заполненными базовыми полями
        """
        # Получаем настройки пользователя
        user_prefs = self.prefs.get(user_name, {})
        display_name = display_name or user_prefs.get('display_name', user_name)
        
        # График работы
        schedule = schedule or WorkSchedule.from_preferences(user_prefs)
        
        # День недели
        weekday = pd.Timestamp(date).day_name()
        day_settings = schedule.get_day_settings(date)
        is_workday = day_settings['is_workday']
        
        # Проверяем, есть ли записи для этого пользователя в этот день
        if (user_name, date) in grouped.groups:
            group = grouped.get_group((user_name, date))
            
            # Используем ВСЕ записи (без фильтрации ночных)
            first_entry = group['timestamp'].min()
            last_entry = group['timestamp'].max()
            arrival_time = first_entry.time()
            departure_time = last_entry.time()
            
            # Расчет рабочих часов
            work_duration = (
                datetime.combine(date, departure_time) -
                datetime.combine(date, arrival_time)
            )
            work_hours = work_duration.total_seconds() / 3600
            
            # Количество появлений
            appearances = len(group)
        else:
            # Отсутствие - нет записей в логах
            arrival_time = None
            departure_time = None
            work_hours = 0
            appearances = 0
        
        # Создаём запись
        return AttendanceRecord(
            date=date,
            user_name=user_name,
            display_name=display_name,
            arrival_time=arrival_time,
            departure_time=departure_time,
            work_hours=work_hours,
            appearances=appearances,
            weekday=weekday,
            is_workday=is_workday,
            schedule_start=day_settings['start_time'],
            schedule_end=day_settings['end_time'],
            expected_hours=day_settings['expected_hours']
        )
