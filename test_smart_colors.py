#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест системы умных цветов
"""

from utils.smart_colors import ColorCalculator

# Создаем калькулятор с дефолтной темой
calc = ColorCalculator()

print("=" * 70)
print("ДЕМОНСТРАЦИЯ СИСТЕМЫ УМНЫХ ЦВЕТОВ")
print("=" * 70)

# 1. Базовые цвета темы
print("\n1. БАЗОВЫЕ ЦВЕТА ТЕМЫ:")
print(f"   Нейтральный (белый):   #{calc.scheme.neutral}")
print(f"   Предупреждение (оранж): #{calc.scheme.warning}")
print(f"   Ошибка (красный):      #{calc.scheme.error}")
print(f"   Успех (зеленый):       #{calc.scheme.success}")
print(f"   Инфо (желтый):         #{calc.scheme.info}")

# 2. Градация опозданий
print("\n2. ГРАДАЦИЯ ОПОЗДАНИЙ (желтый, агрессивная):")
for minutes in [0, 5, 10, 15, 25, 30, 40, 60, 90, 120]:
    color = calc.calculate_late_color(minutes)
    print(f"   {minutes:3d} мин → #{color}")

# 3. Градация раннего ухода
print("\n3. ГРАДАЦИЯ РАННЕГО УХОДА (от белого к желтому):")
for minutes in [0, 15, 30, 60, 90, 120]:
    color = calc.calculate_early_leave_color(minutes)
    print(f"   {minutes:3d} мин → #{color}")

# 4. Градация переработки
print("\n4. ГРАДАЦИЯ ПЕРЕРАБОТКИ (от белого к зеленому):")
for hours in [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]:
    color = calc.calculate_overtime_color(hours)
    print(f"   {hours:.1f}ч → #{color}")

# 5. Градация недоработки
print("\n5. ГРАДАЦИЯ НЕДОРАБОТКИ (оранжевый, АГРЕССИВНАЯ):")
for hours in [0, 0.25, 0.5, 1.0, 1.5, 2.0, 3.0, 6.0, 9.0]:
    color = calc.calculate_underwork_color(hours)
    print(f"   {hours:.2f}ч → #{color}")

# 6. Комбинированные сценарии
print("\n6. КОМБИНИРОВАННЫЕ СЦЕНАРИИ:")
print("   Формат: (приход → уход)")

scenarios = [
    (0, 0, 0, 0, "Норма"),
    (30, 0, 0, 0, "Опоздание 30мин (желтый)"),
    (0, 30, 0, 0, "Ранний уход 30мин (желтый)"),
    (30, 30, 0, 0, "Опоздание + Ранний уход (желтые)"),
    (0, 0, 0, 2.0, "Переработка 2ч (зеленый)"),
    (30, 0, 0, 2.0, "Опоздание + Переработка (желтый приход)"),
    (0, 0, 1.0, 0, "Недоработка 1ч (оранжевый)"),
    (0, 0, 2.0, 0, "Недоработка 2ч (ОРАНЖЕВЫЙ)"),
    (30, 0, 1.0, 0, "Опоздал + Недоработал (СМЕСЬ на приходе)"),
    (0, 30, 1.0, 0, "Недоработал + Ранний уход (СМЕСЬ на уходе)"),
    (30, 30, 1.0, 0, "Опоздал + Недоработал + Ранний уход"),
    (60, 0, 2.0, 0, "Сильное опоздание + недоработка"),
]

for late, early, under, over, desc in scenarios:
    arrival, departure = calc.calculate_combined_color(
        late, early, under, over
    )
    print(f"   {desc:35s} → #{arrival} → #{departure}")

# 7. Интерполяция между цветами
print("\n7. ИНТЕРПОЛЯЦИЯ (от белого к красному):")
for ratio in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
    color = calc.interpolate_color("FFFFFF", "FF0000", ratio)
    print(f"   {ratio:.1f} → #{color}")

# 8. Смешивание цветов
print("\n8. СМЕШИВАНИЕ ЦВЕТОВ:")
mixes = [
    ([("FF0000", 0.5), ("00FF00", 0.5)], "Красный + Зеленый"),
    ([("FF0000", 0.7), ("0000FF", 0.3)], "Красный 70% + Синий 30%"),
    ([("FFFFFF", 0.5), ("000000", 0.5)], "Белый + Черный"),
]

for colors, desc in mixes:
    mixed = calc.mix_colors(colors)
    print(f"   {desc:35s} → #{mixed}")

print("\n" + "=" * 70)
print("Все цвета готовы к использованию в Excel отчетах!")
print("=" * 70)
