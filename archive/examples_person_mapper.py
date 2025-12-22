#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Пример использования PersonMapper - все возможности в одном файле
"""

from services import PersonMapper, DataLoader, AttendanceService
from reporters import ExcelReporter
import json


def example_1_basic_usage():
    """Пример 1: Базовое использование"""
    print("=" * 60)
    print("ПРИМЕР 1: Базовое использование PersonMapper")
    print("=" * 60)
    
    # Создание маппера
    mapper = PersonMapper('person_mapping.json')
    
    # Загрузка логов с маппингом
    df = DataLoader.load_logs(
        'LogsCam/vhod.ndjson',
        file_type='ndjson',
        person_mapper=mapper
    )
    
    print(f"\n✅ Загружено {len(df)} событий")
    print(f"✅ Уникальных сотрудников: {df['name'].nunique()}")
    
    # Показать примеры маппинга
    print("\n📋 Примеры маппинга ID -> Имя:")
    for _, row in df[['name', 'display_name']].drop_duplicates().head(5).iterrows():
        print(f"   {row['name']:20} -> {row['display_name']}")


def example_2_add_person():
    """Пример 2: Добавление нового сотрудника"""
    print("\n" + "=" * 60)
    print("ПРИМЕР 2: Добавление нового сотрудника")
    print("=" * 60)
    
    mapper = PersonMapper('person_mapping.json')
    
    # Добавляем нового сотрудника
    success = mapper.add_person(
        person_id='100',
        display_name='Новый Сотрудник',
        original_names=['Новый Сотрудник', 'Н. Сотрудник'],
        workdays=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
        start_time='09:00',
        end_time='18:00',
        work_hours=9
    )
    
    if success:
        print("✅ Сотрудник добавлен")
        
        # Проверяем
        display_name = mapper.get_display_name('100')
        schedule = mapper.get_schedule('100')
        
        print(f"   ID: 100")
        print(f"   Имя: {display_name}")
        print(f"   Расписание: {schedule['start_time']} - {schedule['end_time']}")
        print(f"   Рабочих дней: {len(schedule['workdays'])}")
        
        # Сохраняем (раскомментируйте для реального сохранения)
        # mapper.save_mappings()


def example_3_aliases():
    """Пример 3: Работа с aliases"""
    print("\n" + "=" * 60)
    print("ПРИМЕР 3: Объединение ID через aliases")
    print("=" * 60)
    
    mapper = PersonMapper('person_mapping.json')
    
    # Добавляем alias для существующего сотрудника
    main_id = '54'  # Сергей Бондарь
    
    # Добавляем дополнительные ID
    mapper.add_alias(
        main_id=main_id,
        alias_ids=['sergei_new_card', 'bondar_temp_id']
    )
    
    print(f"✅ Aliases добавлены для ID: {main_id}")
    print(f"   Главное имя: {mapper.get_display_name(main_id)}")
    
    # Проверяем разрешение aliases
    test_ids = ['54', 'sergei_new_card', 'bondar_temp_id']
    
    print("\n📋 Проверка разрешения aliases:")
    for test_id in test_ids:
        resolved = mapper.resolve_person_id(test_id)
        name = mapper.get_display_name(resolved)
        print(f"   {test_id:20} -> {resolved:10} ({name})")


def example_4_custom_schedule():
    """Пример 4: Индивидуальные расписания"""
    print("\n" + "=" * 60)
    print("ПРИМЕР 4: Индивидуальные расписания")
    print("=" * 60)
    
    mapper = PersonMapper('person_mapping.json')
    
    # Добавляем сотрудника с особым графиком (4 дня в неделю)
    mapper.add_person(
        person_id='101',
        display_name='Работник 4/3',
        workdays=['Monday', 'Tuesday', 'Wednesday', 'Thursday'],
        start_time='10:00',
        end_time='19:00',
        work_hours=9
    )
    
    # Добавляем сотрудника с коротким днём
    mapper.add_person(
        person_id='102',
        display_name='Работник 6 часов',
        workdays=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
        start_time='09:00',
        end_time='15:00',
        work_hours=6
    )
    
    print("✅ Добавлены сотрудники с индивидуальными графиками:")
    
    for person_id in ['101', '102']:
        name = mapper.get_display_name(person_id)
        schedule = mapper.get_schedule(person_id)
        
        print(f"\n   {name} ({person_id}):")
        print(f"      Рабочих дней: {len(schedule['workdays'])}")
        print(f"      Время: {schedule['start_time']} - {schedule['end_time']}")
        print(f"      Часов в день: {schedule['work_hours']}")


def example_5_import_from_ndjson():
    """Пример 5: Автоматический импорт из NDJSON"""
    print("\n" + "=" * 60)
    print("ПРИМЕР 5: Импорт сотрудников из NDJSON")
    print("=" * 60)
    
    ndjson_file = 'LogsCam/vhod.ndjson'
    
    # Читаем NDJSON и находим уникальных сотрудников
    unique_persons = {}
    
    with open(ndjson_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            try:
                event = json.loads(line)
                emp_id = event.get('employeeNoString', '')
                name = event.get('name', '')
                
                if emp_id and name and emp_id not in unique_persons:
                    unique_persons[emp_id] = name
                    
            except json.JSONDecodeError:
                continue
    
    print(f"✅ Найдено {len(unique_persons)} уникальных сотрудников")
    print("\n📋 Первые 5:")
    
    for emp_id, name in list(unique_persons.items())[:5]:
        print(f"   ID: {emp_id:15} Имя: {name}")
    
    # Создаём маппинги для всех
    mapper = PersonMapper('person_mapping.json')
    
    added_count = 0
    for emp_id, name in unique_persons.items():
        if emp_id not in mapper.mappings:
            mapper.add_person(
                person_id=emp_id,
                display_name=name,
                original_names=[name]
            )
            added_count += 1
    
    print(f"\n✅ Добавлено новых сотрудников: {added_count}")


def example_6_convert_to_prefs():
    """Пример 6: Конвертация в формат person_prefs.json"""
    print("\n" + "=" * 60)
    print("ПРИМЕР 6: Экспорт в формат person_prefs.json")
    print("=" * 60)
    
    mapper = PersonMapper('person_mapping.json')
    
    # Конвертируем в формат prefs
    prefs = mapper.convert_to_prefs_format()
    
    print(f"✅ Сконвертировано {len(prefs)} профилей")
    
    # Показываем пример
    if prefs:
        first_id = list(prefs.keys())[0]
        first_prefs = prefs[first_id]
        
        print(f"\n📋 Пример профиля (ID: {first_id}):")
        print(json.dumps(first_prefs, ensure_ascii=False, indent=2))
    
    # Сохраняем в файл (раскомментируйте для реального сохранения)
    # with open('person_prefs_exported.json', 'w', encoding='utf-8') as f:
    #     json.dump(prefs, f, ensure_ascii=False, indent=2)
    # print("\n✅ Сохранено в person_prefs_exported.json")


def example_7_full_workflow():
    """Пример 7: Полный цикл работы"""
    print("\n" + "=" * 60)
    print("ПРИМЕР 7: Полный цикл - от NDJSON до Excel отчёта")
    print("=" * 60)
    
    # 1. Инициализация маппера
    mapper = PersonMapper('person_mapping.json')
    print("✅ [1/5] Маппер инициализирован")
    
    # 2. Загрузка логов
    df = DataLoader.load_logs(
        'LogsCam/vhod.ndjson',
        file_type='ndjson',
        person_mapper=mapper
    )
    print(f"✅ [2/5] Загружено {len(df)} событий")
    
    # 3. Конвертация в профили
    prefs = mapper.convert_to_prefs_format()
    print(f"✅ [3/5] Создано {len(prefs)} профилей")
    
    # 4. Анализ посещаемости
    service = AttendanceService(df, prefs)
    records = service.analyze_all()
    print(f"✅ [4/5] Проанализировано {len(records)} записей")
    
    # 5. Генерация отчёта
    excel_reporter = ExcelReporter(records)
    output_file = 'example_report.xlsx'
    success = excel_reporter.generate_report(output_file)
    
    if success:
        print(f"✅ [5/5] Excel отчёт создан: {output_file}")
    else:
        print("❌ [5/5] Ошибка создания отчёта")
    
    print("\n" + "=" * 60)
    print("🎉 Полный цикл завершён успешно!")
    print("=" * 60)


def main():
    """Запуск всех примеров"""
    print("\n" + "🚀" * 30)
    print(" " * 20 + "ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ PersonMapper")
    print("🚀" * 30 + "\n")
    
    try:
        example_1_basic_usage()
        example_2_add_person()
        example_3_aliases()
        example_4_custom_schedule()
        example_5_import_from_ndjson()
        example_6_convert_to_prefs()
        example_7_full_workflow()
        
        print("\n" + "✅" * 30)
        print(" " * 20 + "ВСЕ ПРИМЕРЫ ВЫПОЛНЕНЫ!")
        print("✅" * 30 + "\n")
        
    except FileNotFoundError as e:
        print(f"\n❌ Файл не найден: {e}")
        print("   Убедитесь, что существует person_mapping.json")
        print("   и LogsCam/vhod.ndjson")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
