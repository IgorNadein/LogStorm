#!/usr/bin/env python3
"""
Тест: проверка что aliases работают только с person_mapping.json
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services import DataLoader, PersonMapper


def test_without_mapping():
    """Тест БЕЗ маппинга - ID остаются разными"""
    print("=" * 70)
    print("ТЕСТ 1: БЕЗ person_mapping.json")
    print("=" * 70)
    
    df = DataLoader.load_logs(
        ['LogsCam/vhod.ndjson', 'LogsCam/vihod.ndjson'],
        file_type='ndjson',
        person_mapper=None  # БЕЗ маппинга!
    )
    
    # Проверяем уникальные имена
    unique_names = df['name'].unique()
    print(f"\n📊 Уникальных пользователей: {len(unique_names)}")
    
    # Ищем Меланя
    melanya_ids = [name for name in unique_names if '666' in str(name) or '19' in str(name)]
    print(f"\n🔍 ID с 666 или 19:")
    for name in sorted(melanya_ids):
        count = len(df[df['name'] == name])
        display = df[df['name'] == name]['display_name'].iloc[0]
        print(f"   {name:15} -> '{display}' ({count} записей)")
    
    # Результат
    if '666' in melanya_ids and '19' in melanya_ids:
        print(f"\n✅ ПРАВИЛЬНО: ID '666' и '19' - это РАЗНЫЕ пользователи")
        return True
    else:
        print(f"\n❌ ОШИБКА: ID объединились без маппинга!")
        return False


def test_with_mapping():
    """Тест С маппингом - ID объединяются"""
    print("\n\n" + "=" * 70)
    print("ТЕСТ 2: С person_mapping.json")
    print("=" * 70)
    
    mapper = PersonMapper('person_mapping.json')
    df = DataLoader.load_logs(
        ['LogsCam/vhod.ndjson', 'LogsCam/vihod.ndjson'],
        file_type='ndjson',
        person_mapper=mapper  # С маппингом!
    )
    
    # Проверяем уникальные имена
    unique_names = df['name'].unique()
    print(f"\n📊 Уникальных пользователей: {len(unique_names)}")
    
    # Ищем Меланя
    melanya_ids = [name for name in unique_names if '666' in str(name) or '19' in str(name)]
    print(f"\n🔍 ID с 666 или 19:")
    for name in sorted(melanya_ids):
        count = len(df[df['name'] == name])
        display = df[df['name'] == name]['display_name'].iloc[0]
        print(f"   {name:15} -> '{display}' ({count} записей)")
    
    # Результат - проверяем что 666 исчез, а 19 имеет 44 записи (21+23)
    has_666 = '666' in unique_names
    has_19 = '19' in unique_names
    count_19 = len(df[df['name'] == '19']) if has_19 else 0
    
    if not has_666 and has_19 and count_19 == 44:
        print(f"\n✅ ПРАВИЛЬНО: ID '666' объединён в '19' (44 записи)")
        return True
    else:
        print(f"\n❌ ОШИБКА: ID не объединились правильно!")
        print(f"   has_666={has_666}, has_19={has_19}, count_19={count_19}")
        return False


if __name__ == '__main__':
    result1 = test_without_mapping()
    result2 = test_with_mapping()
    
    print("\n" + "=" * 70)
    print("ИТОГИ:")
    print("=" * 70)
    print(f"  Без маппинга (разные ID): {'✅ PASS' if result1 else '❌ FAIL'}")
    print(f"  С маппингом (объединены): {'✅ PASS' if result2 else '❌ FAIL'}")
    print("=" * 70)
