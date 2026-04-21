#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт настройки LogStorm
Помогает настроить секреты и проверить окружение
"""

import os
import shutil
from pathlib import Path


def print_header(text):
    """Печать заголовка"""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)


def check_env_file():
    """Проверка .env файла"""
    print_header("Проверка файла .env")
    
    env_file = Path(".env")
    
    if env_file.exists():
        print("✅ Файл .env уже существует")
    else:
        print("ℹ️  Файл .env не найден. Для core/collector он не требуется.")


def check_dependencies():
    """Проверка установленных зависимостей"""
    print_header("Проверка зависимостей")
    
    required_packages = {
        'pandas': 'pandas',
        'openpyxl': 'openpyxl',
        'requests': 'requests',
    }
    
    all_installed = True
    
    for package_name, pip_name in required_packages.items():
        try:
            __import__(package_name)
            print(f"✅ {pip_name}")
        except ImportError:
            print(f"❌ {pip_name} - НЕ УСТАНОВЛЕН")
            all_installed = False
    
    if not all_installed:
        print("\n📦 Установите отсутствующие зависимости:")
        print("   pip install -r requirements.txt")
    else:
        print("\n✅ Все зависимости установлены")


def check_data_files():
    """Проверка наличия файлов данных"""
    print_header("Проверка файлов данных")
    
    logs_file = Path("data/attendance.csv")
    mapping_file = Path("person.json")
    
    if logs_file.exists():
        print(f"✅ {logs_file}")
    else:
        print(f"❌ {logs_file} - НЕ НАЙДЕН")
        print("   Создайте CSV файл с логами или используйте NDJSON")
        print("   Для экспорта из СКУД: python tools/export/export_acs_events.py")
    
    if mapping_file.exists():
        print(f"✅ {mapping_file}")
    else:
        print(f"⚠️  {mapping_file} - НЕ НАЙДЕН (необязательный)")
        print("   Можете работать без маппинга с дефолтными настройками")


def print_next_steps():
    """Вывод следующих шагов"""
    print_header("Следующие шаги")
    
    print("1. Убедитесь, что все проверки пройдены (зеленые галочки ✅)")
    print("2. Если есть проблемы, исправьте их согласно подсказкам")
    print("3. Запустите тесты: python -m pytest")
    print("4. Запустите CLI: python main.py")
    print("\n📚 Дополнительная информация:")
    print("   - README.md - основная документация")
    print("   - .env.example - пример файла с секретами")


def main():
    """Главная функция"""
    print("\n" + "🚀"*30)
    print("LogStorm - Настройка окружения")
    print("🚀"*30)
    
    check_dependencies()
    check_env_file()
    check_data_files()
    print_next_steps()
    
    print("\n✨ Настройка завершена!\n")


if __name__ == '__main__':
    main()
