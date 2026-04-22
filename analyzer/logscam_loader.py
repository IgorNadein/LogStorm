#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Загрузчик данных из NDJSON файлов LogsCam (Hikvision СКУД)
"""

import json
import pandas as pd
from typing import Dict, Optional
from utils.event_mapper import EventMapper


class LogsCamLoader:
    """Загрузка и обработка NDJSON событий из LogsCam"""
    
    @staticmethod
    def load_ndjson(path: str, person_mapper=None) -> pd.DataFrame:
        """
        Загрузка событий СКУД из NDJSON файла
        
        Args:
            path: Путь к NDJSON файлу
            person_mapper: Опциональный PersonMapper для маппинга сотрудников
            
        Returns:
            DataFrame с нормализованными событиями
        """
        events = []
        
        with open(path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    event = json.loads(line)
                    events.append(event)
                except json.JSONDecodeError as e:
                    print(f"Ошибка парсинга строки {line_num}: {e}")
                    continue
        
        print(f"Загружено {len(events)} событий из NDJSON")
        
        return LogsCamLoader.load_events(events, person_mapper)

    @staticmethod
    def load_events(events: list[dict], person_mapper=None) -> pd.DataFrame:
        """Load raw event dictionaries into a normalized DataFrame."""
        df = pd.DataFrame(events)
        if df.empty:
            return df
        return LogsCamLoader._normalize_events(df, person_mapper)
    
    @staticmethod
    def _normalize_events(df: pd.DataFrame, person_mapper=None) -> pd.DataFrame:
        """
        Нормализация событий СКУД к формату LogStorm
        
        Args:
            df: DataFrame с сырыми событиями
            person_mapper: Опциональный PersonMapper для маппинга сотрудников
            
        Returns:
            Нормализованный DataFrame (timestamp, name, event_type, etc.)
        """
        # Парсинг времени
        df['timestamp'] = pd.to_datetime(df['time'])
        df['date'] = df['timestamp'].dt.date
        df['time_only'] = df['timestamp'].dt.time
        
        # Маппинг события
        df['event_type'] = df.apply(
            lambda row: EventMapper.get_event_type(
                row.get('major', 0),
                row.get('minor', 0)
            ),
            axis=1
        )

        df['event_description'] = df.apply(
            lambda row: EventMapper.get_event_description(
                row.get('major', 0),
                row.get('minor', 0)
            ),
            axis=1
        )
        
        # Извлечение имени и ID с использованием PersonMapper
        if person_mapper:
            # Сначала извлекаем ID из события
            def extract_and_resolve(row):
                event = row.to_dict()
                # Извлекаем employee_id и name из события
                employee_id = event.get('employeeNoString', '')
                name = event.get('name', '')
                
                # Если нет ID - пытаемся использовать cardNo
                if not employee_id:
                    card_no = event.get('cardNo', '')
                    if card_no and card_no != '0':
                        employee_id = str(card_no)
                
                # Если всё ещё нет ID - используем имя
                if not employee_id:
                    employee_id = name if name else 'unknown'
                
                # Разрешаем главный ID через PersonMapper
                person_id = person_mapper.resolve_person_id(employee_id, name)
                display_name = person_mapper.get_display_name(person_id)
                
                return person_id, display_name
            
            person_data = df.apply(extract_and_resolve, axis=1)
            df['name'] = [data[0] for data in person_data]  # person_id
            df['display_name'] = [data[1] for data in person_data]  # display name
        else:
            # Без маппера - используем старую логику
            df['name'] = df.apply(
                LogsCamLoader._extract_person_identifier,
                axis=1
            )
            # Копируем name в display_name только если маппера нет
            df['display_name'] = df['name']
        
        # Фильтрация только валидных проходов
        df['is_valid_pass'] = df.apply(
            lambda row: EventMapper.is_valid_pass(
                row.get('major', 0),
                row.get('minor', 0)
            ),
            axis=1
        )
        
        return df
    
    @staticmethod
    def _extract_person_identifier(row: pd.Series) -> str:
        """
        Извлечение идентификатора человека из события БЕЗ маппинга.
        Использует employeeNoString как основной ID (не name!).
        Без PersonMapper каждый ID остаётся отдельным пользователем.
        
        Args:
            row: Строка DataFrame с событием
            
        Returns:
            Идентификатор (employeeNo, cardNo или name)
        """
        # Приоритет 1: employeeNoString (основной ID в СКУД)
        if pd.notna(row.get('employeeNoString')):
            emp_no = str(row['employeeNoString']).strip()
            if emp_no:
                return emp_no  # Возвращаем ID как есть
        
        # Приоритет 2: cardNo
        if pd.notna(row.get('cardNo')):
            card_no = str(row['cardNo']).strip()
            if card_no and card_no != '0':
                return f"card_{card_no}"
        
        # Приоритет 3: Поле name (если нет ID)
        if pd.notna(row.get('name')) and row.get('name'):
            return str(row['name']).strip()
        
        # Неизвестный
        return "unknown"
    
    @staticmethod
    def filter_valid_passes(df: pd.DataFrame) -> pd.DataFrame:
        """
        Фильтрация только валидных проходов (вход/выход)
        
        Args:
            df: DataFrame с событиями
            
        Returns:
            DataFrame только с валидными проходами
        """
        if df.empty:
            return df

        initial_count = len(df)
        df_filtered = df[df['is_valid_pass'] == True].copy()  # noqa: E712
        filtered_count = len(df_filtered)
        
        print(
            f"Отфильтровано: {initial_count} -> {filtered_count} "
            f"(только валидные проходы)"
        )
        
        return df_filtered
    
    @staticmethod
    def get_statistics(df: pd.DataFrame) -> Dict:
        """
        Получить статистику по событиям
        
        Args:
            df: DataFrame с событиями
            
        Returns:
            Словарь со статистикой
        """
        stats = {
            'total_events': len(df),
            'unique_persons': df['name'].nunique(),
            'date_range': (
                df['date'].min() if len(df) > 0 else None,
                df['date'].max() if len(df) > 0 else None
            ),
            'event_types': df['event_type'].value_counts().to_dict()
            if 'event_type' in df.columns else {},
        }
        
        return stats
