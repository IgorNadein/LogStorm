#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест загрузки множественных файлов
"""

from services.data_loader import DataLoader
import pandas as pd
import os
from datetime import datetime

def test_multiple_files():
    """Тестирование загрузки нескольких файлов"""
    
    print("="*60)
    print("Тест: Множественная загрузка файлов")
    print("="*60)
    
    # Тест 1: Создание тестовых файлов
    print("\n[Тест 1] Создание тестовых CSV файлов")
    
    test_dir = "test_temp"
    os.makedirs(test_dir, exist_ok=True)
    
    # Файл 1
    df1 = pd.DataFrame({
        'timestamp': [datetime(2025, 10, 1, 8, 0)],
        'camera': ['main'],
        'name': ['user1'],
        'distance': [0.5],
        'identity': ['photo1.jpg']
    })
    df1.to_csv(f"{test_dir}/file1.csv", index=False)
    
    # Файл 2
    df2 = pd.DataFrame({
        'timestamp': [datetime(2025, 10, 2, 9, 0)],
        'camera': ['main'],
        'name': ['user2'],
        'distance': [0.6],
        'identity': ['photo2.jpg']
    })
    df2.to_csv(f"{test_dir}/file2.csv", index=False)
    
    print("✅ Созданы 2 тестовых файла")
    
    # Тест 2: Загрузка одного файла (обратная совместимость)
    print("\n[Тест 2] Одиночный файл")
    df_single = DataLoader.load_logs(f"{test_dir}/file1.csv")
    print(f"Записей: {len(df_single)}")
    assert len(df_single) == 1, "Должна быть 1 запись"
    print("✅ Прошёл")
    
    # Тест 3: Загрузка нескольких файлов
    print("\n[Тест 3] Множественные файлы")
    files = [f"{test_dir}/file1.csv", f"{test_dir}/file2.csv"]
    df_multi = DataLoader.load_logs(files)
    
    print(f"Записей: {len(df_multi)}")
    assert len(df_multi) == 2, "Должно быть 2 записи"
    print("✅ Прошёл")
    
    # Тест 4: Проверка сортировки
    print("\n[Тест 4] Сортировка по времени")
    print(f"Первая запись: {df_multi.iloc[0]['timestamp']}")
    print(f"Вторая запись: {df_multi.iloc[1]['timestamp']}")
    
    first_ts = df_multi.iloc[0]['timestamp']
    second_ts = df_multi.iloc[1]['timestamp']
    assert first_ts < second_ts, "Должна быть сортировка по времени"
    print("✅ Прошёл")
    
    # Очистка
    import shutil
    shutil.rmtree(test_dir)
    print("\n🗑️ Тестовые файлы удалены")
    
    # Тест 5: Реальные файлы (если есть)
    print("\n[Тест 5] Реальные файлы (опционально)")
    
    csv_file = "logs/attendance.csv"
    ndjson_file = "LogsCam/events_with_pic.ndjson"
    
    real_files = []
    if os.path.exists(csv_file):
        real_files.append(csv_file)
        print(f"✅ Найден: {csv_file}")
    if os.path.exists(ndjson_file):
        real_files.append(ndjson_file)
        print(f"✅ Найден: {ndjson_file}")
    
    if len(real_files) >= 2:
        print(f"\nЗагрузка {len(real_files)} реальных файлов...")
        df_real = DataLoader.load_logs(real_files, file_type='auto')
        print(f"✅ Загружено {len(df_real)} записей")
        print(f"   Уникальных пользователей: {df_real['name'].nunique()}")
        print(f"   Период: {df_real['date'].min()} - {df_real['date'].max()}")
    else:
        print("⏭️ Недостаточно реальных файлов для теста")
    
    print("\n" + "="*60)
    print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
    print("="*60)
    print("\n💡 Система поддерживает множественную загрузку файлов")


if __name__ == '__main__':
    test_multiple_files()
