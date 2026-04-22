#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест логики для выходных дней
"""

from datetime import date, time
from core.models import AttendanceRecord
from analyzer import TechnicalIssueAnalyzer, StatusAnalyzer


def test_weekend_visit():
    """Тест: сотрудник пришел в свой выходной день"""
    
    # Создаем запись: человек пришел в субботу (его выходной) на 3 часа
    record = AttendanceRecord(
        date=date(2025, 1, 11),  # Суббота
        user_name="test_user",
        display_name="Тестовый Пользователь",
        arrival_time=time(10, 0),
        departure_time=time(13, 0),
        work_hours=3.0,
        appearances=2,  # Приход и уход
        weekday="Saturday",
        is_workday=False,  # Это выходной день
        schedule_start=time(9, 0),
        schedule_end=time(18, 0),
        expected_hours=9.0
    )
    
    # Анализируем статусы
    is_late, late_minutes = StatusAnalyzer.analyze_late(record)
    is_early_leave, early_minutes = StatusAnalyzer.analyze_early_leave(record)
    is_underwork = StatusAnalyzer.analyze_underwork(record)
    is_overtime = StatusAnalyzer.analyze_overtime(record)
    
    record.is_late = is_late
    record.late_minutes = late_minutes
    record.is_early_leave = is_early_leave
    record.early_leave_minutes = early_minutes
    record.is_underwork = is_underwork
    record.is_overtime = is_overtime
    
    # Анализируем технические сбои
    analyzer = TechnicalIssueAnalyzer(
        mass_absence_dates=set(),
        critical_absence_dates=set()
    )
    technical_issues = analyzer.analyze(record, None)  # None т.к. нет DataFrame
    
    print("=== Тест: посещение в выходной день ===")
    print(f"Дата: {record.date} ({record.weekday})")
    print(f"Рабочий день: {record.is_workday}")
    print(f"Время: {record.arrival_time} - {record.departure_time}")
    print(f"Отработано часов: {record.work_hours}")
    print()
    print("Статусы:")
    print(f"  Опоздание: {record.is_late} ({record.late_minutes} мин)")
    print(f"  Ранний уход: {record.is_early_leave} ({record.early_leave_minutes} мин)")
    print(f"  Недоработка: {record.is_underwork}")
    print(f"  Переработка: {record.is_overtime}")
    print()
    print("Технические сбои:")
    if technical_issues:
        for issue in technical_issues:
            print(f"  - {issue}")
    else:
        print("  Нет")
    print()
    
    # Проверяем ожидания
    assert not is_late, "В выходной день не должно быть опоздания"
    assert not is_underwork, "В выходной день не должно быть недоработки"
    assert is_overtime, "Любая работа в выходной = переработка"
    assert len(technical_issues) == 0, "В выходной день не должно быть технических сбоев"
    
    print("✅ Все проверки пройдены!")
    print()
    print("Вывод для Excel:")
    print("  - Ячейка НЕ будет красной (нет технических сбоев)")
    print("  - Ячейка НЕ будет желтой (опоздания/недоработки игнорируются)")
    print("  - Ячейка будет белой (форматирование переработки применяется только для рабочих дней)")


if __name__ == "__main__":
    test_weekend_visit()
