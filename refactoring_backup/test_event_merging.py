#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест объединения событий из vhod и vihod
"""

import sys
import os

# Activate venv if needed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services import DataLoader, PersonMapper

def test_event_merging():
    """Проверка объединения событий"""
    print("="*60)
    print("🔍 Тест объединения событий vhod + vihod")
    print("="*60)
    
    # Загружаем маппер
    mapper = PersonMapper('person_mapping.json')
    print(f"\n✅ Маппер загружен:")
    print(f"   Сотрудников: {len(mapper.mappings)}")
    print(f"   Алиасов: {len(mapper.aliases)}")
    
    # Загружаем файлы
    files = ['LogsCam/vhod.ndjson', 'LogsCam/vihod.ndjson']
    print(f"\n📂 Загрузка файлов...")
    
    df = DataLoader.load_logs(
        files,
        file_type='ndjson',
        person_mapper=mapper
    )
    
    print(f"\n✅ Загружено {len(df)} записей")
    print(f"   Колонки: {list(df.columns)}")
    
    # Проверяем уникальные значения
    print(f"\n📊 Уникальные значения:")
    print(f"   name (person_id): {df['name'].nunique()} уникальных")
    print(f"   display_name: {df['display_name'].nunique()} уникальных")
    
    # Показываем примеры
    print(f"\n📋 Примеры записей:")
    print(f"{'name (ID)':<20} | {'display_name':<30}")
    print("-" * 52)
    
    for _, row in df[['name', 'display_name']].drop_duplicates().head(10).iterrows():
        print(f"{row['name']:<20} | {row['display_name']:<30}")
    
    # Проверяем группировку
    print(f"\n🔍 Проверка группировки:")
    grouped = df.groupby(['name', 'date']).size().reset_index(name='count')
    print(f"   Групп по (name, date): {len(grouped)}")
    
    # Показываем пример сотрудника с событиями из обоих файлов
    print(f"\n🔍 Проверка объединения для сотрудника ID='54' (Сергей Бондарь):")
    person_54 = df[df['name'] == '54']
    print(f"   Всего событий: {len(person_54)}")
    print(f"   Уникальных дат: {person_54['date'].nunique()}")
    print(f"   Даты: {sorted(person_54['date'].unique())[:5]}")
    
    # Проверяем конвертацию в prefs
    print(f"\n🔍 Проверка prefs:")
    prefs = mapper.convert_to_prefs_format()
    print(f"   Профилей создано: {len(prefs)}")
    print(f"   Ключи prefs: {list(prefs.keys())[:5]}")
    
    # Проверяем фильтрацию
    print(f"\n🔍 Проверка фильтрации:")
    df_filtered = DataLoader.filter_known_users(df, prefs)
    print(f"   До фильтрации: {len(df)} записей")
    print(f"   После фильтрации: {len(df_filtered)} записей")
    print(f"   Уникальных пользователей: {df_filtered['name'].nunique()}")
    
    # Проверяем, что алиасы объединяются
    print(f"\n🔍 Проверка алиасов:")
    for main_id, aliases in mapper.aliases.items():
        print(f"   Главный ID: {main_id}, алиасы: {aliases}")
        # Проверяем, есть ли события с алиасами
        for alias in aliases:
            alias_events = df[df['name'] == alias]
            if len(alias_events) > 0:
                print(f"      ⚠️ Найдены события с алиасом '{alias}': {len(alias_events)}")
            else:
                print(f"      ✅ Алиас '{alias}' не найден в исходных данных (ОК)")
        
        # Проверяем события главного ID
        main_events = df_filtered[df_filtered['name'] == main_id]
        print(f"      ✅ События главного ID '{main_id}': {len(main_events)}")
    
    print("\n" + "="*60)
    print("✅ Тест завершён")
    print("="*60)


if __name__ == '__main__':
    test_event_merging()
