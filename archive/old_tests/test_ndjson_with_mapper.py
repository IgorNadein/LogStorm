#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для работы с логами СКУД в формате NDJSON
Демонстрирует работу PersonMapper для:
1. Изменения имён сотрудников
2. Установки индивидуальных расписаний
3. Объединения нескольких ID в одного человека (aliases)
"""

import os
from services import DataLoader, PersonMapper, AttendanceService
from reporters import SummaryReporter, ExcelReporter
from config import PERSON_MAPPING_FILE

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def main():
    print("=" * 80)
    print("LogStorm - Тест работы с NDJSON логами СКУД")
    print("=" * 80)
    
    # Путь к NDJSON файлу
    ndjson_file = 'LogsCam/vhod.ndjson'
    
    if not os.path.exists(ndjson_file):
        print(f"❌ Файл {ndjson_file} не найден!")
        return
    
    # [1] Загрузка PersonMapper
    print("\n[1/6] Инициализация PersonMapper...")
    person_mapper = None
    
    if os.path.exists(PERSON_MAPPING_FILE):
        person_mapper = PersonMapper(PERSON_MAPPING_FILE)
        print(f"✅ PersonMapper загружен из {PERSON_MAPPING_FILE}")
    else:
        print(f"⚠️ Файл {PERSON_MAPPING_FILE} не найден")
        print("    Работаем без маппинга (будут использованы имена из логов)")
    
    # [2] Загрузка логов
    print(f"\n[2/6] Загрузка логов из {ndjson_file}...")
    df = DataLoader.load_logs(
        ndjson_file,
        file_type='ndjson',
        person_mapper=person_mapper
    )
    
    print(f"✅ Загружено {len(df)} событий")
    print(f"   Уникальных сотрудников: {df['name'].nunique()}")
    print(f"   Период: {df['date'].min()} - {df['date'].max()}")
    
    # Показываем примеры маппинга
    if 'display_name' in df.columns:
        print("\n   📋 Примеры маппинга:")
        unique_persons = df[['name', 'display_name']].drop_duplicates()
        for _, row in unique_persons.head(10).iterrows():
            print(f"      {row['name']:20} -> {row['display_name']}")
    
    # [3] Подготовка профилей для AttendanceService
    print("\n[3/6] Подготовка профилей сотрудников...")
    
    if person_mapper:
        # Конвертируем маппинг в формат prefs
        prefs = person_mapper.convert_to_prefs_format()
        print(f"✅ Создано {len(prefs)} профилей из маппинга")
    else:
        # Без маппера - создаём дефолтные профили
        prefs = {}
        unique_names = df['name'].unique()
        for name in unique_names:
            prefs[name] = {
                'display_name': name,
                'workdays': ['Monday', 'Tuesday', 'Wednesday',
                           'Thursday', 'Friday'],
                'start_time': '09:00',
                'end_time': '18:00',
                'work_hours': 9
            }
        print(f"✅ Созданы дефолтные профили для {len(prefs)} сотрудников")
    
    # [4] Анализ посещаемости
    print("\n[4/6] Анализ посещаемости...")
    service = AttendanceService(df, prefs)
    records = service.analyze_all()
    print(f"✅ Проанализировано {len(records)} записей")
    
    # [5] Сводка
    print("\n[5/6] Генерация сводки...")
    summary = SummaryReporter(records)
    summary.print_summary()
    
    # [6] Excel отчёт
    print("\n[6/6] Генерация Excel отчёта...")
    output_file = 'attendance_report_ndjson.xlsx'
    excel_reporter = ExcelReporter(records)
    success = excel_reporter.generate_report(output_file)
    
    if success:
        print(f"✅ Excel отчёт сохранён: {output_file}")
    else:
        print("❌ Ошибка создания Excel отчёта")
    
    print("\n" + "=" * 80)
    print("✅ Анализ завершён!")
    print("=" * 80)
    
    # Дополнительная информация о маппинге
    if person_mapper:
        print("\n📝 Информация о PersonMapper:")
        print(f"   - Загружено маппингов: {len(person_mapper.mappings)}")
        print(f"   - Aliases: {len(person_mapper.aliases)}")
        
        if person_mapper.aliases:
            print("\n   🔗 Настроенные aliases:")
            for main_id, aliases in person_mapper.aliases.items():
                if isinstance(aliases, list):
                    main_name = person_mapper.get_display_name(main_id)
                    print(f"      {main_name} ({main_id})")
                    for alias in aliases:
                        print(f"         └─ {alias}")


if __name__ == '__main__':
    main()
