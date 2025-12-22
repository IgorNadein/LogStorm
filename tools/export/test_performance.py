#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Быстрый тест экспорта с профилированием
Экспортирует только несколько событий для анализа производительности
"""

import subprocess
import sys

def main():
    print("🔍 Тест производительности экспорта событий СКУД")
    print("=" * 60)
    print()
    
    # Параметры для быстрого теста (только 100 событий)
    cmd = [
        sys.executable,
        "export_acs_events.py",
        "--host", "192.168.1.101",
        "--user", "admin",
        "--password", "xZ260616737",
        "--start", "2025-12-18T00:00:00",
        "--end", "2025-12-19T23:59:59",
        "--pic",
        "--out", "test_performance.ndjson",
        "--verbose",  # Включаем подробный вывод
        "--begin-serial", "1",
        "--end-serial", "100",  # Ограничиваем 100 событиями
    ]
    
    print("Запуск команды:")
    print(" ".join(cmd))
    print()
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Ошибка выполнения: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️ Прервано пользователем")
        sys.exit(130)

if __name__ == "__main__":
    main()
