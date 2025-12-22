#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест GUI с NDJSON файлами и PersonMapper
"""

import os
import sys

# Проверка зависимостей
def check_imports():
    """Проверка доступности всех модулей"""
    print("🔍 Проверка зависимостей...")
    
    try:
        from services import DataLoader, PersonMapper
        print("✅ DataLoader, PersonMapper - OK")
    except ImportError as e:
        print(f"❌ Ошибка импорта services: {e}")
        return False
    
    try:
        from config import PERSON_MAPPING_FILE
        print(f"✅ PERSON_MAPPING_FILE = {PERSON_MAPPING_FILE}")
    except ImportError as e:
        print(f"❌ Ошибка импорта config: {e}")
        return False
    
    return True


def test_person_mapper():
    """Тест загрузки PersonMapper"""
    print("\n🔍 Тест PersonMapper...")
    
    from services import PersonMapper
    from config import PERSON_MAPPING_FILE
    
    if not os.path.exists(PERSON_MAPPING_FILE):
        print(f"⚠️ Файл не найден: {PERSON_MAPPING_FILE}")
        print("   Создайте его с помощью: python manage_mapping.py")
        return False
    
    try:
        mapper = PersonMapper(PERSON_MAPPING_FILE)
        print(f"✅ Маппинг загружен")
        print(f"   Сотрудников: {len(mapper.person_mappings)}")
        print(f"   Алиасов: {len(mapper.aliases)}")
        
        # Пример использования
        if mapper.person_mappings:
            first_id = list(mapper.person_mappings.keys())[0]
            display_name = mapper.get_display_name(first_id)
            print(f"   Пример: ID '{first_id}' → '{display_name}'")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка загрузки маппинга: {e}")
        return False


def test_data_loader_with_mapper():
    """Тест DataLoader с PersonMapper"""
    print("\n🔍 Тест DataLoader + PersonMapper...")
    
    from services import DataLoader, PersonMapper
    from config import PERSON_MAPPING_FILE
    
    # Проверяем NDJSON файлы
    ndjson_files = [
        'LogsCam/vhod.ndjson',
        'LogsCam/vihod.ndjson'
    ]
    
    existing_files = [f for f in ndjson_files if os.path.exists(f)]
    
    if not existing_files:
        print(f"⚠️ NDJSON файлы не найдены:")
        for f in ndjson_files:
            print(f"   - {f}")
        return False
    
    try:
        # Загружаем маппер
        mapper = None
        if os.path.exists(PERSON_MAPPING_FILE):
            mapper = PersonMapper(PERSON_MAPPING_FILE)
            print(f"✅ Маппер загружен")
        else:
            print(f"⚠️ Маппер не используется")
        
        # Загружаем данные
        print(f"📂 Загрузка файлов: {len(existing_files)}")
        for f in existing_files:
            print(f"   - {f}")
        
        df = DataLoader.load_logs(
            existing_files if len(existing_files) > 1 else existing_files[0],
            file_type='ndjson',
            person_mapper=mapper
        )
        
        print(f"✅ Загружено записей: {len(df)}")
        
        # Проверяем колонки
        print(f"   Колонки: {list(df.columns)}")
        
        # Показываем примеры имён
        if not df.empty and 'Имя' in df.columns:
            unique_names = df['Имя'].unique()[:5]
            print(f"   Примеры имён ({len(unique_names)}):")
            for name in unique_names:
                print(f"      - {name}")
        
        # Проверяем преобразования маппера
        if mapper and not df.empty:
            print("\n   Проверка маппинга:")
            for _, row in df.head(3).iterrows():
                person_id = row.get('ID сотрудника', 'N/A')
                name = row.get('Имя', 'N/A')
                print(f"      ID: {person_id} → Имя: {name}")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка загрузки данных: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_prefs_conversion():
    """Тест конвертации маппинга в prefs формат"""
    print("\n🔍 Тест конвертации в person_prefs формат...")
    
    from services import PersonMapper
    from config import PERSON_MAPPING_FILE
    
    if not os.path.exists(PERSON_MAPPING_FILE):
        print(f"⚠️ Файл маппинга не найден")
        return False
    
    try:
        mapper = PersonMapper(PERSON_MAPPING_FILE)
        prefs = mapper.convert_to_prefs_format()
        
        print(f"✅ Конвертация успешна")
        print(f"   Профилей создано: {len(prefs)}")
        
        # Показываем пример
        if prefs:
            first_name = list(prefs.keys())[0]
            first_pref = prefs[first_name]
            print(f"\n   Пример профиля '{first_name}':")
            print(f"      Рабочие дни: {first_pref.get('workdays', [])}")
            print(f"      Начало: {first_pref.get('start_time', 'N/A')}")
            print(f"      Конец: {first_pref.get('end_time', 'N/A')}")
            print(f"      Часов: {first_pref.get('work_hours', 'N/A')}")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка конвертации: {e}")
        return False


def main():
    """Запуск всех тестов"""
    print("="*60)
    print("🧪 Тестирование GUI + NDJSON + PersonMapper")
    print("="*60)
    
    results = []
    
    # 1. Проверка импортов
    results.append(("Импорты", check_imports()))
    
    # 2. Тест PersonMapper
    results.append(("PersonMapper", test_person_mapper()))
    
    # 3. Тест DataLoader с маппером
    results.append(("DataLoader+Mapper", test_data_loader_with_mapper()))
    
    # 4. Тест конвертации
    results.append(("Конвертация в prefs", test_prefs_conversion()))
    
    # Итоги
    print("\n" + "="*60)
    print("📊 Результаты тестов:")
    print("="*60)
    
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    print(f"\nПройдено: {passed}/{total}")
    
    if passed == total:
        print("\n✅ Все тесты пройдены! GUI готов к работе с NDJSON.")
        print("\nЗапустите GUI:")
        print("  python gui_app.py")
        print("  или")
        print("  python run_gui.py")
    else:
        print("\n⚠️ Некоторые тесты не прошли. Проверьте ошибки выше.")
    
    print("="*60)


if __name__ == '__main__':
    main()
