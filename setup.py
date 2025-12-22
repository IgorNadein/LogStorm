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
    """Проверка и создание .env файла"""
    print_header("Проверка файла .env")
    
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if env_file.exists():
        print("✅ Файл .env уже существует")
        
        # Проверяем наличие ключа
        with open(env_file, 'r') as f:
            content = f.read()
            if 'your_client_secret_here' in content:
                print("⚠️  ВНИМАНИЕ: API ключ не настроен!")
                print("   Откройте .env и замените 'your_client_secret_here' на ваш ключ")
            elif 'GIGACHAT_API_KEY=' in content and len(content.split('GIGACHAT_API_KEY=')[1].split('\n')[0].strip()) > 10:
                print("✅ API ключ GigaChat настроен")
            else:
                print("⚠️  API ключ не найден или пустой")
    else:
        print("⚠️  Файл .env не найден")
        
        if env_example.exists():
            print("📝 Создание .env из .env.example...")
            shutil.copy(env_example, env_file)
            print("✅ Файл .env создан")
            print("\n📝 ВАЖНО: Откройте .env и настройте API ключ GigaChat!")
            print("   Замените 'your_client_secret_here' на ваш ключ")
        else:
            print("❌ Файл .env.example не найден!")
            print("   Создайте его вручную или переустановите приложение")


def check_dependencies():
    """Проверка установленных зависимостей"""
    print_header("Проверка зависимостей")
    
    required_packages = {
        'pandas': 'pandas',
        'openpyxl': 'openpyxl',
        'gigachat': 'gigachat',
        'dotenv': 'python-dotenv'
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
    mapping_file = Path("person_mapping.json")
    
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


def check_gigachat_key():
    """Проверка настройки GigaChat API ключа"""
    print_header("Проверка GigaChat API ключа")
    
    # Загружаем .env если есть python-dotenv
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("⚠️  python-dotenv не установлен")
    
    api_key = os.environ.get('GIGACHAT_API_KEY')
    
    if api_key:
        if api_key == 'your_client_secret_here':
            print("⚠️  API ключ не настроен (используется значение по умолчанию)")
            print("   Откройте .env и замените его на реальный ключ")
        else:
            # Маскируем ключ для безопасности
            masked_key = api_key[:8] + '...' + api_key[-8:] if len(api_key) > 16 else '***'
            print(f"✅ API ключ найден: {masked_key}")
            print("   Ключ загружен и готов к использованию")
    else:
        print("❌ API ключ не найден")
        print("\n📝 Как настроить:")
        print("   1. Получите ключ на https://developers.sber.ru/gigachat")
        print("   2. Откройте файл .env")
        print("   3. Замените 'your_client_secret_here' на ваш ключ")
        print("   4. Сохраните файл и запустите setup.py снова")


def print_next_steps():
    """Вывод следующих шагов"""
    print_header("Следующие шаги")
    
    print("1. Убедитесь, что все проверки пройдены (зеленые галочки ✅)")
    print("2. Если есть проблемы, исправьте их согласно подсказкам")
    print("3. Запустите приложение: python main.py")
    print("\n📚 Дополнительная информация:")
    print("   - README.md - основная документация")
    print("   - GIGACHAT_SETUP.md - настройка GigaChat API")
    print("   - .env.example - пример файла с секретами")


def main():
    """Главная функция"""
    print("\n" + "🚀"*30)
    print("LogStorm - Настройка окружения")
    print("🚀"*30)
    
    check_dependencies()
    check_env_file()
    check_gigachat_key()
    check_data_files()
    print_next_steps()
    
    print("\n✨ Настройка завершена!\n")


if __name__ == '__main__':
    main()
