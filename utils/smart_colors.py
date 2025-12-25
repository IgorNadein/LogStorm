#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Система умных цветов для Excel отчетов

Автоматически вычисляет градации и смешивания цветов
на основе базовых цветов и степени серьезности событий.
"""

from typing import Tuple, List, Optional
from config.colors import ColorScheme, default_color_scheme


class ColorCalculator:
    """Вычисление умных цветов на основе серьезности и комбинаций"""
    
    def __init__(self, scheme: Optional[ColorScheme] = None):
        """
        Args:
            scheme: Цветовая схема с порогами (если None - дефолт)
        """
        self.scheme = scheme or default_color_scheme
        
        # Для обратной совместимости
        self.theme = self.scheme
    
    @staticmethod
    def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
        """
        Конвертация HEX в RGB
        
        Args:
            hex_color: "FF0000" или "#FF0000"
        
        Returns:
            (r, g, b) - кортеж 0-255
        """
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    @staticmethod
    def rgb_to_hex(r: int, g: int, b: int) -> str:
        """
        Конвертация RGB в HEX
        
        Args:
            r, g, b: значения 0-255
        
        Returns:
            "FF0000" (без #)
        """
        return f"{r:02X}{g:02X}{b:02X}"
    
    def interpolate_color(
        self,
        color1: str,
        color2: str,
        ratio: float
    ) -> str:
        """
        Интерполяция между двумя цветами
        
        Args:
            color1: Начальный цвет (HEX)
            color2: Конечный цвет (HEX)
            ratio: 0.0-1.0 (0=color1, 1=color2)
        
        Returns:
            Интерполированный цвет (HEX)
        
        Example:
            interpolate_color("FFFFFF", "FF0000", 0.5) 
            # -> "FF8080" (розовый)
        """
        ratio = max(0.0, min(1.0, ratio))  # Ограничиваем 0-1
        
        r1, g1, b1 = self.hex_to_rgb(color1)
        r2, g2, b2 = self.hex_to_rgb(color2)
        
        r = int(r1 + (r2 - r1) * ratio)
        g = int(g1 + (g2 - g1) * ratio)
        b = int(b1 + (b2 - b1) * ratio)
        
        return self.rgb_to_hex(r, g, b)
    
    def mix_colors(
        self,
        colors_with_weights: List[Tuple[str, float]]
    ) -> str:
        """
        Смешивание нескольких цветов с весами
        
        Args:
            colors_with_weights: [(hex_color, weight), ...]
            
        Returns:
            Смешанный цвет (HEX)
        
        Example:
            mix_colors([("FF0000", 0.5), ("00FF00", 0.5)])
            # -> "808000" (смесь красного и зеленого)
        """
        if not colors_with_weights:
            return self.theme.neutral
        
        # Нормализуем веса
        total_weight = sum(w for _, w in colors_with_weights)
        if total_weight == 0:
            return self.theme.neutral
        
        # Взвешенное смешивание RGB
        r_sum, g_sum, b_sum = 0, 0, 0
        
        for color_hex, weight in colors_with_weights:
            r, g, b = self.hex_to_rgb(color_hex)
            normalized_weight = weight / total_weight
            r_sum += r * normalized_weight
            g_sum += g * normalized_weight
            b_sum += b * normalized_weight
        
        return self.rgb_to_hex(
            int(r_sum), int(g_sum), int(b_sum)
        )
    
    def get_severity_color(
        self,
        base_color: str,
        severity: float,
        neutral_color: Optional[str] = None
    ) -> str:
        """
        Получить цвет с градацией от нейтрального к базовому
        
        Args:
            base_color: Базовый цвет (HEX) - для максимальной серьезности
            severity: 0.0-1.0 (0=норма, 1=критично)
            neutral_color: Нейтральный цвет (если None - белый)
        
        Returns:
            Цвет с учетом серьезности (HEX)
        
        Example:
            get_severity_color("FF0000", 0.0) # -> "FFFFFF" (белый)
            get_severity_color("FF0000", 0.5) # -> "FF8080" (розовый)
            get_severity_color("FF0000", 1.0) # -> "FF0000" (красный)
        """
        if neutral_color is None:
            neutral_color = self.theme.neutral
        
        return self.interpolate_color(
            neutral_color,
            base_color,
            severity
        )
    
    def calculate_late_color(self, minutes: int) -> str:
        """
        Цвет опоздания (от белого к желтому)
        
        Использует пороги из scheme.thresholds:
        - late_tolerance_minutes: порог толерантности
        - late_full_severity_minutes: полная интенсивность цвета
        """
        tolerance = self.scheme.thresholds.late_tolerance_minutes
        full_severity = self.scheme.thresholds.late_full_severity_minutes
        
        if minutes <= tolerance:
            return self.scheme.neutral
        
        # Градация от tolerance до full_severity
        severity = min(
            (minutes - tolerance) / (full_severity - tolerance),
            1.0
        )
        return self.get_severity_color(self.scheme.info, severity)
    
    def calculate_early_leave_color(self, minutes: int) -> str:
        """
        Цвет раннего ухода (от белого к желтому)
        
        Использует пороги из scheme.thresholds:
        - early_leave_tolerance_minutes: порог толерантности
        - early_leave_full_severity_minutes: полная интенсивность
        """
        tolerance = self.scheme.thresholds.early_leave_tolerance_minutes
        full_severity = (
            self.scheme.thresholds.early_leave_full_severity_minutes
        )
        
        if minutes <= tolerance:
            return self.scheme.neutral
        
        # Градация от tolerance до full_severity
        severity = min(
            (minutes - tolerance) / (full_severity - tolerance),
            1.0
        )
        return self.get_severity_color(self.scheme.info, severity)
    
    def calculate_underwork_color(self, hours_missing: float) -> str:
        """
        Цвет недоработки (от белого к оранжевому) - АГРЕССИВНЫЙ
        
        Использует пороги из scheme.thresholds:
        - underwork_tolerance_hours: порог толерантности
        - underwork_full_severity_hours: полная интенсивность
        """
        tolerance = self.scheme.thresholds.underwork_tolerance_hours
        full_severity = self.scheme.thresholds.underwork_full_severity_hours
        
        if hours_missing <= tolerance:
            return self.scheme.neutral
        
        # Градация от tolerance до full_severity
        severity = min(
            (hours_missing - tolerance) / (full_severity - tolerance),
            1.0
        )
        return self.get_severity_color(self.scheme.warning, severity)
    
    def calculate_overtime_color(self, hours_extra: float) -> str:
        """
        Цвет переработки (от белого к зеленому)
        
        Использует пороги из scheme.thresholds:
        - overtime_full_severity_hours: полная интенсивность
        """
        if hours_extra <= 0:
            return self.scheme.neutral
        
        full_severity = self.scheme.thresholds.overtime_full_severity_hours
        severity = min(hours_extra / full_severity, 1.0)
        return self.get_severity_color(self.scheme.success, severity)
    
    def calculate_combined_color(
        self,
        late_minutes: int = 0,
        early_leave_minutes: int = 0,
        underwork_hours: float = 0,
        overtime_hours: float = 0
    ) -> Tuple[str, str]:
        """
        Вычислить цвета для ячеек Приход/Уход с учетом комбинаций
        
        Args:
            late_minutes: Минуты опоздания
            early_leave_minutes: Минуты раннего ухода
            underwork_hours: Часы недоработки
            overtime_hours: Часы переработки
        
        Returns:
            (arrival_color, departure_color) - цвета для прихода и ухода
        
        Логика (приоритеты):
        1. Недоработка (оранжевый) - самый высокий приоритет
        2. Опоздание (желтый) - влияет на приход
        3. Ранний уход (желтый) - влияет на уход
        4. Переработка (зеленый) - только если нет проблем
        
        При комбинациях - СМЕШИВАЕМ цвета:
        - Опоздал + недоработал = желтый+оранжевый на приходе
        - Недоработал + ранний уход = оранжевый+желтый на уходе
        """
        arrival_color = self.scheme.neutral
        departure_color = self.scheme.neutral
        
        # === ПРИХОД ===
        colors_arrival = []
        
        # 1. Недоработка влияет на обе ячейки (высший приоритет)
        if underwork_hours > 0:
            underwork_color = self.calculate_underwork_color(underwork_hours)
            # Вес зависит от серьезности недоработки
            underwork_weight = min(underwork_hours / 2.0, 1.0)
            colors_arrival.append((underwork_color, underwork_weight))
        
        # 2. Опоздание влияет на приход
        if late_minutes > 0:
            late_color = self.calculate_late_color(late_minutes)
            # Вес зависит от минут опоздания
            late_weight = min(late_minutes / 60.0, 1.0)
            colors_arrival.append((late_color, late_weight))
        
        # 3. Переработка - только если нет проблем
        if overtime_hours > 0 and not colors_arrival:
            arrival_color = self.calculate_overtime_color(overtime_hours)
        elif colors_arrival:
            # Смешиваем все цвета для прихода
            arrival_color = self.mix_colors(colors_arrival)
        
        # === УХОД ===
        colors_departure = []
        
        # 1. Недоработка влияет на обе ячейки
        if underwork_hours > 0:
            underwork_color = self.calculate_underwork_color(underwork_hours)
            underwork_weight = min(underwork_hours / 2.0, 1.0)
            colors_departure.append((underwork_color, underwork_weight))
        
        # 2. Ранний уход влияет на уход
        if early_leave_minutes > 0:
            early_color = self.calculate_early_leave_color(
                early_leave_minutes
            )
            early_weight = min(early_leave_minutes / 60.0, 1.0)
            colors_departure.append((early_color, early_weight))
        
        # 3. Переработка - только если нет проблем
        if overtime_hours > 0 and not colors_departure:
            departure_color = self.calculate_overtime_color(overtime_hours)
        elif colors_departure:
            # Смешиваем все цвета для ухода
            departure_color = self.mix_colors(colors_departure)
        
        return (arrival_color, departure_color)


# Глобальный экземпляр с дефолтной темой
default_calculator = ColorCalculator()
