#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Утилита для управления person_mapping.json
Позволяет добавлять, редактировать и удалять маппинги сотрудников
"""

import sys
import json
from analyzer import PersonMapper
from core.models import WorkSchedule
from core.settings import PERSON_MAPPING_FILE, SAMPLE_PERSON_MAPPING_FILE


def print_menu():
    """Вывод главного меню"""
    print("\n" + "=" * 60)
    print("   Управление маппингом сотрудников (PersonMapper)")
    print("=" * 60)
    print("1. Показать всех сотрудников")
    print("2. Добавить нового сотрудника")
    print("3. Редактировать сотрудника")
    print("4. Добавить alias")
    print("5. Показать все aliases")
    print("6. Импортировать из NDJSON")
    print("7. Экспортировать в person_prefs.json")
    print("0. Выход")
    print("=" * 60)


def show_all_persons(mapper):
    """Показать всех сотрудников"""
    print("\n📋 Список сотрудников:")
    print("-" * 80)
    print(f"{'ID':15} {'Имя':30} {'Рабочие дни':10} {'Часы'}")
    print("-" * 80)
    
    for person_id in sorted(mapper.get_all_person_ids()):
        display_name = mapper.get_display_name(person_id)
        schedule = mapper.get_schedule(person_id)
        workdays_count = len(schedule.workdays)
        hours = f"{schedule.start_time}-{schedule.end_time}"
        
        print(f"{person_id:15} {display_name:30} {workdays_count} дней    {hours}")
    
    print("-" * 80)
    print(f"Всего: {len(mapper.get_all_person_ids())} сотрудников")


def add_person(mapper):
    """Добавить нового сотрудника"""
    print("\n➕ Добавление нового сотрудника")
    print("-" * 60)
    
    person_id = input("ID сотрудника (из СКУД): ").strip()
    if not person_id:
        print("❌ ID не может быть пустым")
        return False
    
    if person_id in mapper.mappings:
        print(f"⚠️ Сотрудник с ID '{person_id}' уже существует")
        return False
    
    display_name = input("Отображаемое имя: ").strip()
    if not display_name:
        print("❌ Имя не может быть пустым")
        return False
    
    # Оригинальные имена
    print("\nВарианты имени в СКУД (через запятую):")
    original_input = input(f"[по умолчанию: {display_name}]: ").strip()
    if original_input:
        original_names = [n.strip() for n in original_input.split(',')]
    else:
        original_names = [display_name]
    
    # Рабочие дни
    print("\nРабочие дни (1-Пн, 2-Вт, 3-Ср, 4-Чт, 5-Пт, 6-Сб, 7-Вс):")
    workdays_input = input("[по умолчанию: 1-5 (Пн-Пт)]: ").strip()
    
    day_map = {
        '1': 'Monday', '2': 'Tuesday', '3': 'Wednesday',
        '4': 'Thursday', '5': 'Friday', '6': 'Saturday', '7': 'Sunday'
    }
    
    if workdays_input:
        try:
            days = [d.strip() for d in workdays_input.replace(',', ' ').split()]
            workdays = [day_map[d] for d in days if d in day_map]
        except KeyError:
            print("⚠️ Неверный формат дней, используем Пн-Пт")
            workdays = ['Monday', 'Tuesday', 'Wednesday',
                       'Thursday', 'Friday']
    else:
        workdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    
    # Время работы
    start_time = input("Время начала [09:00]: ").strip() or "09:00"
    end_time = input("Время окончания [18:00]: ").strip() or "18:00"
    work_hours_input = input("Часов работы [9]: ").strip()
    work_hours = int(work_hours_input) if work_hours_input else 9
    
    # Добавляем
    schedule = WorkSchedule(
        start_time=start_time,
        end_time=end_time,
        workdays=workdays,
        expected_hours=work_hours,
    )
    success = mapper.add_person(
        person_id=person_id,
        display_name=display_name,
        original_names=original_names,
        schedule=schedule,
    )
    
    if success:
        print(f"\n✅ Сотрудник '{display_name}' успешно добавлен!")
        return True
    else:
        print("\n❌ Ошибка при добавлении сотрудника")
        return False


def edit_person(mapper):
    """Редактировать существующего сотрудника"""
    print("\n✏️ Редактирование сотрудника")
    print("-" * 60)
    
    person_id = input("ID сотрудника для редактирования: ").strip()
    
    if person_id not in mapper.mappings:
        print(f"❌ Сотрудник с ID '{person_id}' не найден")
        return False
    
    person_data = mapper.mappings[person_id]
    
    print(f"\nТекущие данные:")
    print(f"  Имя: {person_data.get('display_name')}")
    print(f"  Оригинальные имена: {person_data.get('original_names')}")
    print(f"  Рабочие дни: {len(person_data.get('workdays', []))} дней")
    print(f"  Время: {person_data.get('start_time')}"
          f" - {person_data.get('end_time')}")
    print(f"  Часов: {person_data.get('work_hours')}")
    
    print("\nВведите новые значения (Enter - оставить текущее):")
    
    # Новые значения
    display_name = input(
        f"Имя [{person_data.get('display_name')}]: "
    ).strip()
    if display_name:
        person_data['display_name'] = display_name
    
    start_time = input(
        f"Время начала [{person_data.get('start_time')}]: "
    ).strip()
    if start_time:
        person_data['start_time'] = start_time
    
    end_time = input(
        f"Время окончания [{person_data.get('end_time')}]: "
    ).strip()
    if end_time:
        person_data['end_time'] = end_time
    
    work_hours = input(
        f"Часов работы [{person_data.get('work_hours')}]: "
    ).strip()
    if work_hours:
        person_data['work_hours'] = int(work_hours)
    
    print(f"\n✅ Сотрудник '{person_data['display_name']}' обновлён!")
    return True


def add_alias(mapper):
    """Добавить alias для объединения ID"""
    print("\n🔗 Добавление alias")
    print("-" * 60)
    
    main_id = input("Главный ID: ").strip()
    
    if main_id not in mapper.mappings:
        print(f"❌ Сотрудник с ID '{main_id}' не найден")
        print("   Сначала создайте профиль для главного ID")
        return False
    
    print(f"Главный ID: {main_id} ({mapper.get_display_name(main_id)})")
    print("\nДополнительные ID (через запятую):")
    alias_input = input("ID: ").strip()
    
    if not alias_input:
        print("❌ Не указаны дополнительные ID")
        return False
    
    alias_ids = [aid.strip() for aid in alias_input.split(',')]
    
    # Добавляем
    success = mapper.add_alias(main_id, alias_ids)
    
    if success:
        print(f"\n✅ Aliases добавлены для '{mapper.get_display_name(main_id)}':")
        for aid in alias_ids:
            print(f"   • {aid}")
        return True
    else:
        print("\n❌ Ошибка при добавлении aliases")
        return False


def show_aliases(mapper):
    """Показать все aliases"""
    print("\n🔗 Список aliases:")
    print("-" * 80)
    
    if not mapper.aliases:
        print("Aliases не настроены")
        return
    
    for main_id, alias_list in mapper.aliases.items():
        if isinstance(alias_list, list) and main_id in mapper.mappings:
            main_name = mapper.get_display_name(main_id)
            print(f"\n{main_name} ({main_id}):")
            for alias in alias_list:
                print(f"   └─ {alias}")
    
    print("-" * 80)


def import_from_ndjson(mapper):
    """Импорт уникальных сотрудников из NDJSON"""
    print("\n📥 Импорт из NDJSON")
    print("-" * 60)
    
    file_path = input("Путь к NDJSON файлу: ").strip()
    
    try:
        import json
        
        persons = {}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    event = json.loads(line)
                    emp_id = event.get('employeeNoString', '')
                    name = event.get('name', '')
                    
                    if emp_id and name and emp_id not in mapper.mappings:
                        persons[emp_id] = name
                        
                except json.JSONDecodeError:
                    continue
        
        if not persons:
            print("⚠️ Новые сотрудники не найдены")
            return False
        
        print(f"\nНайдено {len(persons)} новых сотрудников:")
        for emp_id, name in persons.items():
            print(f"  • {emp_id}: {name}")
        
        confirm = input("\nДобавить всех? (y/n): ").strip().lower()
        if confirm != 'y':
            print("❌ Отменено")
            return False
        
        # Добавляем всех
        for emp_id, name in persons.items():
            mapper.add_person(
                person_id=emp_id,
                display_name=name,
                original_names=[name]
            )
        
        print(f"✅ Добавлено {len(persons)} сотрудников!")
        return True
        
    except FileNotFoundError:
        print(f"❌ Файл {file_path} не найден")
        return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


def export_to_prefs(mapper):
    """Экспорт в формат person_prefs.json"""
    print("\n📤 Экспорт в person_prefs.json")
    print("-" * 60)
    
    output_file = input(
        "Файл для сохранения [person_prefs_export.json]: "
    ).strip()
    if not output_file:
        output_file = "person_prefs_export.json"
    
    try:
        prefs = mapper.convert_to_prefs_format()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(prefs, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Экспортировано {len(prefs)} профилей в {output_file}")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


def resolve_mapping_file(mapping_file=None):
    return mapping_file or PERSON_MAPPING_FILE or SAMPLE_PERSON_MAPPING_FILE


def main(mapping_file=None):
    """Главная функция"""
    print("\n🚀 Запуск утилиты управления маппингом...")
    
    # Загружаем маппер
    mapping_path = resolve_mapping_file(mapping_file)
    try:
        mapper = PersonMapper(mapping_path)
    except Exception as e:
        print(f"❌ Ошибка загрузки: {e}")
        sys.exit(1)
    
    changed = False
    
    while True:
        print_menu()
        choice = input("\nВыберите действие: ").strip()
        
        if choice == '0':
            # Выход
            if changed:
                save = input("\n💾 Сохранить изменения? (y/n): ").strip().lower()
                if save == 'y':
                    if mapper.save_mappings():
                        print("✅ Изменения сохранены!")
                    else:
                        print("❌ Ошибка сохранения")
            print("\n👋 До свидания!")
            break
            
        elif choice == '1':
            show_all_persons(mapper)
            
        elif choice == '2':
            if add_person(mapper):
                changed = True
            
        elif choice == '3':
            if edit_person(mapper):
                changed = True
            
        elif choice == '4':
            if add_alias(mapper):
                changed = True
            
        elif choice == '5':
            show_aliases(mapper)
            
        elif choice == '6':
            if import_from_ndjson(mapper):
                changed = True
            
        elif choice == '7':
            export_to_prefs(mapper)
            
        else:
            print("❌ Неверный выбор")
        
        input("\nНажмите Enter для продолжения...")


if __name__ == '__main__':
    main()
