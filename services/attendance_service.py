#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сервис анализа посещаемости
"""

import pandas as pd
from datetime import datetime
from typing import List
from models import AttendanceRecord, WorkSchedule
from validators import AbsenceValidator
from analyzers import TechnicalIssueAnalyzer, StatusAnalyzer


class AttendanceService:
    """
    Основной сервис анализа посещаемости
    
    Координирует работу валидаторов и анализаторов для определения
    всех статусов пользователей за все дни.
    """
    
    def __init__(self, df: pd.DataFrame, prefs: dict,
                 device_mapping: dict = None):
        """
        Args:
            df: DataFrame с логами посещаемости
            prefs: Словарь с настройками пользователей
            device_mapping: Опциональный словарь с маппингом камер
                {
                    'arrival_devices': ['IP1', 'IP2'],
                    'departure_devices': ['IP3', 'IP4']
                }
        """
        self.df = df
        self.prefs = prefs
        self.device_mapping = device_mapping
        
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
    
    def _analyze_user_day(self, user_name: str, date, grouped) -> AttendanceRecord:
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
        record = self._create_base_record(user_name, date, grouped)
        
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
    
    def _create_base_record(self, user_name: str, date, grouped) -> AttendanceRecord:
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
        display_name = user_prefs.get('display_name', user_name)
        
        # График работы
        schedule = WorkSchedule.from_preferences(user_prefs)
        
        # День недели
        weekday = pd.Timestamp(date).day_name()
        is_workday = schedule.is_workday(weekday)
        
        # Проверяем, есть ли записи для этого пользователя в этот день
        if (user_name, date) in grouped.groups:
            group = grouped.get_group((user_name, date))
            
            # Фильтрация по камерам (если настройка device_mapping задана)
            if self.device_mapping and '_device' in group.columns:
                arrival_devices = self.device_mapping.get(
                    'arrival_devices', []
                )
                departure_devices = self.device_mapping.get(
                    'departure_devices', []
                )
                
                # Фильтруем события по камерам
                arrival_group = group[
                    group['_device'].isin(arrival_devices)
                ]
                departure_group = group[
                    group['_device'].isin(departure_devices)
                ]
                
                # Приход: ТОЛЬКО с камеры входа (строго)
                if not arrival_group.empty:
                    first_entry_idx = arrival_group['timestamp'].idxmin()
                    first_entry = arrival_group.loc[
                        first_entry_idx, 'timestamp'
                    ]
                    arrival_time = first_entry.time()
                    arrival_photo_path = arrival_group.loc[
                        first_entry_idx
                    ].get('_imagePath', None)
                else:
                    # Нет событий с камеры входа - не фиксируем приход
                    arrival_time = None
                    arrival_photo_path = None
                
                # Уход: ТОЛЬКО с камеры выхода (строго)
                if not departure_group.empty:
                    last_entry_idx = departure_group['timestamp'].idxmax()
                    last_entry = departure_group.loc[
                        last_entry_idx, 'timestamp'
                    ]
                    departure_time = last_entry.time()
                    departure_photo_path = departure_group.loc[
                        last_entry_idx
                    ].get('_imagePath', None)
                else:
                    # Нет событий с камеры выхода - не фиксируем уход
                    departure_time = None
                    departure_photo_path = None
            else:
                # Без фильтрации - используем ВСЕ записи
                first_entry_idx = group['timestamp'].idxmin()
                last_entry_idx = group['timestamp'].idxmax()
                
                first_entry = group.loc[first_entry_idx, 'timestamp']
                last_entry = group.loc[last_entry_idx, 'timestamp']
                
                arrival_time = first_entry.time()
                departure_time = last_entry.time()
                
                # Извлекаем пути к фото из поля _imagePath (если есть)
                arrival_photo_path = group.loc[first_entry_idx].get(
                    '_imagePath', None
                )
                departure_photo_path = group.loc[last_entry_idx].get(
                    '_imagePath', None
                )
            
            # Расчет рабочих часов (только если есть и приход и уход)
            if arrival_time is not None and departure_time is not None:
                work_duration = (
                    datetime.combine(date, departure_time) -
                    datetime.combine(date, arrival_time)
                )
                work_hours = work_duration.total_seconds() / 3600
            else:
                # Если нет прихода или ухода - не можем вычислить часы
                work_hours = 0
            
            # Количество появлений
            appearances = len(group)
        else:
            # Отсутствие - нет записей в логах
            arrival_time = None
            departure_time = None
            work_hours = 0
            appearances = 0
            arrival_photo_path = None
            departure_photo_path = None
        
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
            schedule_start=schedule.start_time,
            schedule_end=schedule.end_time,
            expected_hours=schedule.expected_hours,
            arrival_photo_path=arrival_photo_path,
            departure_photo_path=departure_photo_path
        )
