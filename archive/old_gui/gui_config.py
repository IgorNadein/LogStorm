#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Конфигурация GUI приложения LogStorm
"""

import os

# Пути по умолчанию
DEFAULT_CSV_PATH = os.path.join("logs", "attendance.csv")
DEFAULT_NDJSON_PATH = os.path.join("LogsCam", "events_with_pic.ndjson")
DEFAULT_PREFS_PATH = "person_mapping.json"  # Используем person_mapping.json
DEFAULT_OUTPUT_PATH = os.path.join("reports", "attendance_report.xlsx")

# Настройки окна
WINDOW_TITLE = "LogStorm - Анализатор посещаемости"
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
WINDOW_MIN_WIDTH = 700
WINDOW_MIN_HEIGHT = 500

# Цвета
COLOR_PRIMARY = "#2196F3"
COLOR_SUCCESS = "#4CAF50"
COLOR_WARNING = "#FF9800"
COLOR_ERROR = "#F44336"
COLOR_BG = "#F5F5F5"
COLOR_TEXT = "#212121"

# Стили
FONT_FAMILY = "Segoe UI"
FONT_SIZE_TITLE = 16
FONT_SIZE_NORMAL = 10
FONT_SIZE_SMALL = 9

# Тексты
TEXT_WELCOME = """
Добро пожаловать в LogStorm!

Система анализа посещаемости сотрудников с поддержкой:
• CSV файлов (camera logs)
• NDJSON файлов (Hikvision СКУД)
• Умная классификация проблем
• AI анализ через GigaChat
• Excel отчеты с цветовым кодированием

Выберите файлы и запустите анализ.
"""

# Типы файлов для диалогов
FILE_TYPES_LOGS = [
    ("Все лог-файлы", "*.csv *.ndjson *.jsonl"),
    ("CSV файлы", "*.csv"),
    ("NDJSON файлы", "*.ndjson *.jsonl"),
    ("Все файлы", "*.*")
]

FILE_TYPES_JSON = [
    ("JSON файлы", "*.json"),
    ("Все файлы", "*.*")
]

FILE_TYPES_EXCEL = [
    ("Excel файлы", "*.xlsx"),
    ("Все файлы", "*.*")
]
