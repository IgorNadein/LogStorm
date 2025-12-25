#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Загрузчик данных из SQLite базы коллектора
"""

import pandas as pd
import sqlite3
from typing import Optional, List
from datetime import datetime, date


class SQLiteLoader:
    """Загрузка событий из SQLite базы данных"""
    
    def __init__(self, db_path: str):
        """
        Args:
            db_path: Путь к SQLite базе данных
        """
        self.db_path = db_path
    
    def load_events(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        devices: Optional[List[str]] = None,
        person_mapper=None
    ) -> pd.DataFrame:
        """
        Загрузка событий из БД с фильтрацией
        
        Args:
            start_date: Начальная дата (включительно)
            end_date: Конечная дата (включительно)
            devices: Список IP адресов устройств для фильтрации
            person_mapper: Опциональный PersonMapper для маппинга
            
        Returns:
            DataFrame с событиями
        """
        conn = sqlite3.connect(self.db_path)
        
        # Построение SQL запроса
        query = "SELECT * FROM events WHERE 1=1"
        params = []
        
        if start_date:
            query += " AND date(time) >= ?"
            params.append(start_date.isoformat())
        
        if end_date:
            query += " AND date(time) <= ?"
            params.append(end_date.isoformat())
        
        if devices:
            placeholders = ','.join('?' * len(devices))
            query += f" AND device IN ({placeholders})"
            params.extend(devices)
        
        query += " ORDER BY time"
        
        # Загрузка данных
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        if df.empty:
            return df
        
        # Распаковка JSON из event_data
        df = self._unpack_event_data(df)
        
        # Преобразование типов для совместимости с AttendanceService
        df['timestamp'] = pd.to_datetime(df['time'])
        df['date'] = df['timestamp'].dt.date
        df['time_only'] = df['timestamp'].dt.time
        df['time'] = df['time']  # Оставляем оригинальную строку времени
        
        # Применение маппинга сотрудников (если есть)
        if person_mapper:
            df = self._apply_person_mapping(df, person_mapper)
        
        return df
    
    def _apply_person_mapping(
        self, df: pd.DataFrame, person_mapper
    ) -> pd.DataFrame:
        """Применение маппинга имён сотрудников"""
        # Создаём колонки для маппинга
        mapping_data = df.apply(
            lambda row: self._get_mapped_data(
                row.get('employeeNoString', ''),
                row.get('name', ''),
                person_mapper
            ),
            axis=1
        )
        
        # Распаковываем person_id и display_name
        df['name'] = [data[0] for data in mapping_data]
        df['display_name'] = [data[1] for data in mapping_data]
        
        return df
    
    def _unpack_event_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Распаковка JSON из колонки event_data
        
        Извлекает важные поля из JSON (включая _imagePath)
        и добавляет их как отдельные колонки
        """
        import json
        
        def extract_fields(event_data_json: str) -> dict:
            """Извлечь нужные поля из JSON"""
            try:
                data = json.loads(event_data_json)
                return {
                    '_imagePath': data.get('_imagePath'),
                    '_device': data.get('_device'),
                    '_device_name': data.get('_device_name'),
                    'pictureURL': data.get('pictureURL')
                }
            except (json.JSONDecodeError, TypeError):
                return {
                    '_imagePath': None,
                    '_device': None,
                    '_device_name': None,
                    'pictureURL': None
                }
        
        # Извлекаем поля из JSON
        extracted = df['event_data'].apply(extract_fields)
        
        # Добавляем как новые колонки
        df['_imagePath'] = [row['_imagePath'] for row in extracted]
        df['_device'] = [row['_device'] for row in extracted]
        df['_device_name'] = [row['_device_name'] for row in extracted]
        df['pictureURL'] = [row['pictureURL'] for row in extracted]
        
        return df
    
    def _get_mapped_data(
        self, employee_id: str, original_name: str, person_mapper
    ) -> tuple:
        """
        Получить маппированные person_id и display_name
        
        Returns:
            (person_id, display_name)
        """
        try:
            # Разрешаем person_id через employee_id и имя
            person_id = person_mapper.resolve_person_id(
                employee_id, original_name
            )
            # Получаем отображаемое имя
            display_name = person_mapper.get_display_name(person_id)
            return (person_id, display_name)
        except Exception:
            # Если маппинг не удался - возвращаем оригинальные данные
            return (employee_id or original_name, original_name)
    
    def get_device_list(self) -> List[str]:
        """Получить список всех устройств в БД"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT device, device_name
            FROM events
            ORDER BY device
        """)
        
        devices = [
            {'host': row[0], 'name': row[1]}
            for row in cursor.fetchall()
        ]
        
        conn.close()
        return devices
    
    def get_date_range(self) -> tuple[Optional[date], Optional[date]]:
        """Получить диапазон дат в БД"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT
                date(MIN(time)) as min_date,
                date(MAX(time)) as max_date
            FROM events
        """)
        
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0] and row[1]:
            min_date = datetime.fromisoformat(row[0]).date()
            max_date = datetime.fromisoformat(row[1]).date()
            return min_date, max_date
        
        return None, None
    
    def get_stats(self) -> dict:
        """Получить статистику по БД"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Общее количество событий
        cursor.execute("SELECT COUNT(*) FROM events")
        total_events = cursor.fetchone()[0]
        
        # Количество устройств
        cursor.execute("SELECT COUNT(DISTINCT device) FROM events")
        total_devices = cursor.fetchone()[0]
        
        # Количество уникальных сотрудников
        cursor.execute("""
            SELECT COUNT(DISTINCT employeeNoString)
            FROM events
            WHERE employeeNoString IS NOT NULL
        """)
        total_employees = cursor.fetchone()[0]
        
        # Диапазон дат
        cursor.execute("""
            SELECT
                date(MIN(time)) as min_date,
                date(MAX(time)) as max_date
            FROM events
        """)
        row = cursor.fetchone()
        
        conn.close()
        
        return {
            'total_events': total_events,
            'total_devices': total_devices,
            'total_employees': total_employees,
            'date_range': (row[0], row[1]) if row else (None, None)
        }
