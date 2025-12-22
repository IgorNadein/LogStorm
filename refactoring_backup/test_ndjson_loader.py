#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест загрузчика NDJSON
"""

from services.logscam_loader import LogsCamLoader
import os

def test_ndjson_loader():
    """Тестирование загрузчика NDJSON"""
    
    ndjson_path = "LogsCam/events_with_pic.ndjson"
    
    if not os.path.exists(ndjson_path):
        print(f"❌ Файл не найден: {ndjson_path}")
        return
    
    print("="*60)
    print("Тест загрузчика NDJSON")
    print("="*60)
    
    # Загрузка
    print("\n[1] Загрузка NDJSON...")
    df = LogsCamLoader.load_ndjson(ndjson_path)
    print(f"✅ Загружено {len(df)} событий")
    
    # Статистика
    print("\n[2] Статистика...")
    stats = LogsCamLoader.get_statistics(df)
    print(f"  Всего событий: {stats['total_events']}")
    print(f"  Уникальных людей: {stats['unique_persons']}")
    print(f"  Период: {stats['date_range'][0]} - {stats['date_range'][1]}")
    print(f"\n  Типы событий:")
    for event_type, count in stats['event_types'].items():
        print(f"    {event_type}: {count}")
    
    # Фильтрация валидных проходов
    print("\n[3] Фильтрация валидных проходов...")
    df_valid = LogsCamLoader.filter_valid_passes(df)
    print(f"✅ Валидных проходов: {len(df_valid)}")
    
    # Примеры
    print("\n[4] Примеры данных...")
    print("\nПервые 5 валидных проходов:")
    print(df_valid[['timestamp', 'name', 'event_type', 'event_description']].head())
    
    print("\n" + "="*60)
    print("✅ ТЕСТ ЗАВЕРШЁН УСПЕШНО")
    print("="*60)


if __name__ == '__main__':
    test_ndjson_loader()
