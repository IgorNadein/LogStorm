#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест работы БЕЗ файла профилей
"""

from services.data_loader import DataLoader
import os

def test_without_prefs():
    """Тестирование работы без person_prefs.json"""
    
    print("="*60)
    print("Тест: Работа БЕЗ файла профилей")
    print("="*60)
    
    # Тест 1: Несуществующий файл
    print("\n[Тест 1] Несуществующий файл профилей")
    prefs = DataLoader.load_preferences("nonexistent.json")
    print(f"Результат: {prefs}")
    assert prefs == {}, "Должен вернуть пустой словарь"
    print("✅ Прошёл")
    
    # Тест 2: None
    print("\n[Тест 2] path=None")
    prefs = DataLoader.load_preferences(None)
    print(f"Результат: {prefs}")
    assert prefs == {}, "Должен вернуть пустой словарь"
    print("✅ Прошёл")
    
    # Тест 3: Фильтрация с пустыми prefs
    print("\n[Тест 3] Фильтрация без профилей")
    
    # Создаём тестовый DataFrame
    import pandas as pd
    from datetime import datetime
    
    test_data = {
        'name': ['user1', 'user2', 'user3'] * 3,
        'timestamp': [datetime.now()] * 9,
        'date': [datetime.now().date()] * 9,
        'time': [datetime.now().time()] * 9
    }
    df = pd.DataFrame(test_data)
    
    print(f"Исходных записей: {len(df)}")
    print(f"Уникальных пользователей: {df['name'].nunique()}")
    
    df_filtered = DataLoader.filter_known_users(df, {})
    
    print(f"После фильтрации: {len(df_filtered)}")
    assert len(df_filtered) == len(df), "Должны остаться все записи"
    print("✅ Прошёл")
    
    # Тест 4: Реальный файл NDJSON без профилей
    print("\n[Тест 4] Реальный NDJSON без профилей")
    ndjson_path = "LogsCam/events_with_pic.ndjson"
    
    if os.path.exists(ndjson_path):
        print(f"Загрузка: {ndjson_path}")
        df_real = DataLoader.load_logs(ndjson_path, file_type='ndjson')
        print(f"Загружено записей: {len(df_real)}")
        print(f"Уникальных пользователей: {df_real['name'].nunique()}")
        
        # Фильтрация без профилей
        df_real_filtered = DataLoader.filter_known_users(df_real, {})
        print(f"После фильтрации: {len(df_real_filtered)}")
        
        assert len(df_real_filtered) == len(df_real), "Все должны остаться"
        print("✅ Прошёл")
    else:
        print("⏭️ Пропущен (файл не найден)")
    
    print("\n" + "="*60)
    print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
    print("="*60)
    print("\n💡 Система теперь может работать БЕЗ person_prefs.json")


if __name__ == '__main__':
    test_without_prefs()
