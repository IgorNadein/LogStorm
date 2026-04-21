#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сервис загрузки данных
"""

import pandas as pd
import json
import os


class DataLoader:
    """Загрузка данных из файлов"""
    
    @staticmethod
    def load_logs(path, file_type: str = 'auto',
                  person_mapper=None) -> pd.DataFrame:
        """
        Загрузка логов посещаемости из CSV, NDJSON или SQLite
        
        Args:
            path: Путь к файлу (str) или список путей (list)
            file_type: Тип файла ('csv', 'ndjson', 'sqlite', 'auto')
            person_mapper: Опциональный PersonMapper для маппинга сотрудников
            
        Returns:
            DataFrame с логами (timestamp, date, time)
        """
        # Если передан список файлов - загружаем и объединяем
        if isinstance(path, list):
            return DataLoader._load_multiple_files(
                path, file_type, person_mapper
            )
        
        # Одиночный файл - оригинальная логика
        return DataLoader._load_single_file(path, file_type, person_mapper)
    
    @staticmethod
    def _load_single_file(path: str, file_type: str = 'auto',
                         person_mapper=None) -> pd.DataFrame:
        """
        Загрузка одного файла логов
        
        Args:
            path: Путь к файлу с логами
            file_type: Тип файла ('csv', 'ndjson', 'auto')
            person_mapper: Опциональный PersonMapper для маппинга сотрудников
            
        Returns:
            DataFrame с логами
        """
        # Автоопределение типа файла
        if file_type == 'auto':
            ext = os.path.splitext(path)[1].lower()
            if ext in ['.ndjson', '.jsonl']:
                file_type = 'ndjson'
            elif ext == '.csv':
                file_type = 'csv'
            elif ext in ['.db', '.sqlite', '.sqlite3']:
                file_type = 'sqlite'
            else:
                # Попытка определить по содержимому
                with open(path, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                    if first_line.startswith('{'):
                        file_type = 'ndjson'
                    else:
                        file_type = 'csv'
        
        # Загрузка в зависимости от типа
        if file_type == 'ndjson':
            from analyzer.logscam_loader import LogsCamLoader
            df = LogsCamLoader.load_ndjson(path, person_mapper)
            df = LogsCamLoader.filter_valid_passes(df)
        elif file_type in ['sqlite', 'db']:
            from core.repositories import CollectorEventRepository
            from analyzer.logscam_loader import LogsCamLoader
            repo = CollectorEventRepository(path)
            events = repo.load_raw_events()
            print(f"Загружено {len(events)} событий из SQLite")
            df = LogsCamLoader.load_events(events, person_mapper)
            df = LogsCamLoader.filter_valid_passes(df)
        else:
            # CSV загрузка (оригинальная логика)
            df = pd.read_csv(path, on_bad_lines='skip')
            if 'name' in df.columns:
                df['name'] = df['name'].astype(str)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['date'] = df['timestamp'].dt.date
            df['time'] = df['timestamp'].dt.time
        
        return df
    
    @staticmethod
    def _load_multiple_files(paths: list, file_type: str = 'auto',
                            person_mapper=None) -> pd.DataFrame:
        """
        Загрузка и объединение нескольких файлов логов
        
        Args:
            paths: Список путей к файлам
            file_type: Тип файлов ('csv', 'ndjson', 'sqlite', 'auto')
            person_mapper: Опциональный PersonMapper для маппинга сотрудников
            
        Returns:
            Объединённый DataFrame
        """
        print(f"\n[INFO] Загрузка {len(paths)} файлов...")
        
        dfs = []
        for i, path in enumerate(paths, 1):
            print(f"  [{i}/{len(paths)}] {os.path.basename(path)}...", end=" ")
            try:
                df = DataLoader._load_single_file(
                    path, file_type, person_mapper
                )
                dfs.append(df)
                print(f"✅ {len(df)} записей")
            except Exception as e:
                print(f"❌ Ошибка: {e}")
                continue
        
        if not dfs:
            raise RuntimeError("Не удалось загрузить ни одного файла!")
        
        # Объединяем все DataFrame
        print("\n🔗 Объединение данных...")
        combined_df = pd.concat(dfs, ignore_index=True)
        
        # Сортируем по времени
        combined_df = combined_df.sort_values('timestamp')
        combined_df = combined_df.reset_index(drop=True)
        
        print(
            f"✅ Итого: {len(combined_df)} записей "
            f"из {len(dfs)} файлов"
        )
        
        return combined_df
    
    @staticmethod
    def load_preferences(path: str = None) -> dict:
        """
        Загрузка настроек пользователей из JSON
        
        Args:
            path: Путь к JSON файлу с настройками (опционально)
            
        Returns:
            Словарь {user_id: {display_name, start_time, end_time, workdays}}
            Пустой словарь, если path=None или файл не существует
        """
        if path is None or not os.path.exists(path):
            print(
                "⚠️ Файл профилей не найден - "
                "используются дефолтные настройки"
            )
            return {}
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                prefs = json.load(f)
                print(f"✅ Загружено {len(prefs)} профилей сотрудников")
                return prefs
        except Exception as e:
            print(f"⚠️ Ошибка загрузки профилей: {e}")
            return {}
    
    @staticmethod
    def filter_known_users(df: pd.DataFrame, prefs: dict) -> pd.DataFrame:
        """
        Фильтрация только пользователей с профилями
        
        Args:
            df: DataFrame с логами
            prefs: Словарь с настройками пользователей (может быть пустым)
            
        Returns:
            Отфильтрованный DataFrame
        """
        initial_count = len(df)
        
        # Если профили не заданы - анализируем всех
        if not prefs:
            print(
                f"ℹ️ Профили не заданы - анализируются все {initial_count} "
                f"записей ({df['name'].nunique()} уникальных пользователей)"
            )
            return df
        
        # Если профили есть - фильтруем
        known_users = set(prefs.keys())
        df_filtered = df[df['name'].isin(known_users)]
        filtered_count = len(df_filtered)
        
        print(
            f"Отфильтровано: {initial_count} -> {filtered_count} записей "
            f"(только пользователи с профилями)"
        )
        
        return df_filtered
