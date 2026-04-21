#!/usr/bin/env python3
"""Тест: aliases работают только при явном PersonMapper."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from analyzer import DataLoader, PersonMapper

NDJSON_FILES = ['data/vhod.ndjson', 'data/vihod.ndjson']
MAPPING_FILE = 'person.json'


def test_without_mapping():
    """Тест БЕЗ маппинга - ID остаются разными"""
    print("=" * 70)
    print("ТЕСТ 1: БЕЗ person.json")
    print("=" * 70)
    
    df = DataLoader.load_logs(
        NDJSON_FILES,
        file_type='ndjson',
        person_mapper=None  # БЕЗ маппинга!
    )
    
    # Проверяем уникальные имена
    unique_names = df['name'].unique()
    print(f"\n📊 Уникальных пользователей: {len(unique_names)}")
    
    # Ищем Employee Alpha Alias
    melanya_ids = [name for name in unique_names if '666' in str(name) or '19' in str(name)]
    print(f"\n🔍 ID с 666 или 19:")
    for name in sorted(melanya_ids):
        count = len(df[df['name'] == name])
        display = df[df['name'] == name]['display_name'].iloc[0]
        print(f"   {name:15} -> '{display}' ({count} записей)")
    
    # Результат
    assert '666' in melanya_ids
    assert '19' in melanya_ids


def test_with_mapping():
    """Тест С маппингом - ID объединяются"""
    print("\n\n" + "=" * 70)
    print("ТЕСТ 2: С person.json")
    print("=" * 70)
    
    mapper = PersonMapper(MAPPING_FILE)
    df = DataLoader.load_logs(
        NDJSON_FILES,
        file_type='ndjson',
        person_mapper=mapper  # С маппингом!
    )
    
    # Проверяем уникальные имена
    unique_names = df['name'].unique()
    print(f"\n📊 Уникальных пользователей: {len(unique_names)}")
    
    # Ищем Employee Alpha Alias
    melanya_ids = [name for name in unique_names if '666' in str(name) or '19' in str(name)]
    print(f"\n🔍 ID с 666 или 19:")
    for name in sorted(melanya_ids):
        count = len(df[df['name'] == name])
        display = df[df['name'] == name]['display_name'].iloc[0]
        print(f"   {name:15} -> '{display}' ({count} записей)")
    
    # Результат - проверяем что 666 исчез, а записи попали в основной ID 19
    has_666 = '666' in unique_names
    has_19 = '19' in unique_names
    count_19 = len(df[df['name'] == '19']) if has_19 else 0
    
    assert not has_666
    assert has_19
    assert count_19 > 0


if __name__ == '__main__':
    result1 = test_without_mapping()
    result2 = test_with_mapping()
    
    print("\n" + "=" * 70)
    print("ИТОГИ:")
    print("=" * 70)
    print(f"  Без маппинга (разные ID): {'✅ PASS' if result1 else '❌ FAIL'}")
    print(f"  С маппингом (объединены): {'✅ PASS' if result2 else '❌ FAIL'}")
    print("=" * 70)
