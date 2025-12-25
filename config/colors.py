#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Color Configuration - настройки цветовой схемы для умных цветов
"""

from dataclasses import dataclass


@dataclass
class ColorThresholds:
    """Пороги толерантности для расчета цветов"""
    
    # Опоздания
    late_tolerance_minutes: int = 5
    late_full_severity_minutes: int = 60
    
    # Ранний уход
    early_leave_tolerance_minutes: int = 5
    early_leave_full_severity_minutes: int = 60
    
    # Недоработка (более агрессивная)
    underwork_tolerance_hours: float = 0.25
    underwork_full_severity_hours: float = 2.0
    
    # Переработка
    overtime_full_severity_hours: float = 3.0


@dataclass
class ColorScheme:
    """Базовые цвета для умной системы градаций"""
    
    # Базовые цвета (HEX без #)
    neutral: str = "FFFFFF"     # Белый - норма
    warning: str = "FFA500"     # Оранжевый - предупреждение
    error: str = "FF0000"       # Красный - ошибка
    success: str = "00B050"     # Зеленый - успех
    info: str = "FFFF00"        # Желтый - информация
    
    # Пороги
    thresholds: ColorThresholds = None
    
    def __post_init__(self):
        if self.thresholds is None:
            self.thresholds = ColorThresholds()


# Глобальный экземпляр с дефолтными значениями
default_color_scheme = ColorScheme()


def load_color_scheme_from_dict(data: dict) -> ColorScheme:
    """
    Загрузить цветовую схему из словаря (из config.json)
    
    Args:
        data: Словарь с настройками цветов
    
    Returns:
        ColorScheme с загруженными значениями
    """
    colors = data.get('colors', {})
    thresholds_data = data.get('thresholds', {})
    
    # Создаем пороги
    thresholds = ColorThresholds(
        late_tolerance_minutes=thresholds_data.get(
            'late_tolerance_minutes', 5
        ),
        late_full_severity_minutes=thresholds_data.get(
            'late_full_severity_minutes', 60
        ),
        early_leave_tolerance_minutes=thresholds_data.get(
            'early_leave_tolerance_minutes', 5
        ),
        early_leave_full_severity_minutes=thresholds_data.get(
            'early_leave_full_severity_minutes', 60
        ),
        underwork_tolerance_hours=thresholds_data.get(
            'underwork_tolerance_hours', 0.25
        ),
        underwork_full_severity_hours=thresholds_data.get(
            'underwork_full_severity_hours', 2.0
        ),
        overtime_full_severity_hours=thresholds_data.get(
            'overtime_full_severity_hours', 3.0
        )
    )
    
    # Создаем схему
    return ColorScheme(
        neutral=colors.get('neutral', 'FFFFFF'),
        warning=colors.get('warning', 'FFA500'),
        error=colors.get('error', 'FF0000'),
        success=colors.get('success', '00B050'),
        info=colors.get('info', 'FFFF00'),
        thresholds=thresholds
    )


def save_color_scheme_to_dict(scheme: ColorScheme) -> dict:
    """
    Сохранить цветовую схему в словарь (для config.json)
    
    Args:
        scheme: ColorScheme для сохранения
    
    Returns:
        Словарь с настройками цветов
    """
    return {
        'colors': {
            'neutral': scheme.neutral,
            'warning': scheme.warning,
            'error': scheme.error,
            'success': scheme.success,
            'info': scheme.info
        },
        'thresholds': {
            'late_tolerance_minutes': scheme.thresholds.late_tolerance_minutes,
            'late_full_severity_minutes': (
                scheme.thresholds.late_full_severity_minutes
            ),
            'early_leave_tolerance_minutes': (
                scheme.thresholds.early_leave_tolerance_minutes
            ),
            'early_leave_full_severity_minutes': (
                scheme.thresholds.early_leave_full_severity_minutes
            ),
            'underwork_tolerance_hours': (
                scheme.thresholds.underwork_tolerance_hours
            ),
            'underwork_full_severity_hours': (
                scheme.thresholds.underwork_full_severity_hours
            ),
            'overtime_full_severity_hours': (
                scheme.thresholds.overtime_full_severity_hours
            )
        }
    }
