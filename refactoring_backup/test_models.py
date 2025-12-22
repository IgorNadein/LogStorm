#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест моделей данных
"""

from datetime import date, time
from models import AttendanceRecord, WorkSchedule


def test_work_schedule():
    """Тест WorkSchedule"""
    print("=== Тест WorkSchedule ===")
    
    schedule = WorkSchedule(
        start_time=time(9, 0),
        end_time=time(18, 0),
        workdays=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
        expected_hours=9.0
    )
    
    print(f"График: {schedule.start_time} - {schedule.end_time}")
    print(f"Ожидаемо часов: {schedule.expected_hours}")
    print(f"Понедельник рабочий? {schedule.is_workday('Monday')}")
    print(f"Суббота рабочая? {schedule.is_workday('Saturday')}")
    
    # Тест from_preferences
    user_prefs = {
        'start_time': '08:00',
        'end_time': '17:00',
        'workdays': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    }
    
    schedule2 = WorkSchedule.from_preferences(user_prefs)
    print(f"\nИз preferences: {schedule2.start_time} - {schedule2.end_time}")
    print(f"Ожидаемо часов: {schedule2.expected_hours}")
    
    print("✅ WorkSchedule работает!\n")


def test_attendance_record():
    """Тест AttendanceRecord"""
    print("=== Тест AttendanceRecord ===")
    
    record = AttendanceRecord(
        date=date(2025, 11, 5),
        user_name='john_doe',
        display_name='Иван Иванов',
        arrival_time=time(9, 15),
        departure_time=time(17, 30),
        work_hours=8.25,
        appearances=5,
        weekday='Tuesday',
        is_workday=True,
        schedule_start=time(9, 0),
        schedule_end=time(18, 0),
        expected_hours=9.0,
        is_late=True,
        late_minutes=15
    )
    
    record.employee_issues.append("Опоздание 15 мин")
    
    print(f"Пользователь: {record.display_name}")
    print(f"Дата: {record.date}, День: {record.weekday}")
    print(f"Приход: {record.arrival_time}, Уход: {record.departure_time}")
    print(f"Отработано: {record.work_hours}ч (ожидалось {record.expected_hours}ч)")
    print(f"Опоздание: {record.is_late} ({record.late_minutes} мин)")
    print(f"Валидная запись: {record.is_valid_record}")
    print(f"Проблемы сотрудника: {record.employee_issues_text}")
    
    # Тест to_dict
    data_dict = record.to_dict()
    print(f"\nСловарь содержит ключи: {list(data_dict.keys())[:5]}...")
    
    print("✅ AttendanceRecord работает!\n")


if __name__ == '__main__':
    test_work_schedule()
    test_attendance_record()
    print("🎉 Все тесты моделей пройдены!")
