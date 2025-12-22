#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Анализатор технических сбоев системы
"""

import pandas as pd
from datetime import date, datetime
from typing import List, Set, Optional
from models import AttendanceRecord
from validators import TimeValidator


class TechnicalIssueAnalyzer:
    """
    Определение технических сбоев системы учёта
    
    Технические сбои - это проблемы НЕ по вине сотрудника:
    - Массовые/критические отсутствия
    - Ночная активность (аномалия времени)
    - Одно появление (камера не зафиксировала приход/уход)
    - Экстремальное опоздание (>3 часа)
    - Критическая недоработка (<7ч или на 2+ч меньше нормы)
    """
    
    def __init__(self, 
                 mass_absence_dates: Set[date],
                 critical_absence_dates: Set[date]):
        """
        Args:
            mass_absence_dates: Даты с массовым отсутствием (>90%)
            critical_absence_dates: Даты с критическим отсутствием (100%)
        """
        self.mass_absence_dates = mass_absence_dates
        self.critical_absence_dates = critical_absence_dates
    
    def analyze(self, 
                record: AttendanceRecord, 
                entries: Optional[pd.DataFrame]) -> List[str]:
        """
        Анализ технических сбоев для одной записи
        
        Args:
            record: Запись посещаемости
            entries: DataFrame с логами для этого пользователя в этот день
                     (None если записей нет)
        
        Returns:
            Список названий технических сбоев
        """
        issues = []
        
        # 1. Критическое отсутствие (100% - высший приоритет)
        if record.date in self.critical_absence_dates:
            issues.append("День критического отсутствия (100% отсутствуют)")
            return issues  # Остальное не проверяем
        
        # 2. Массовое отсутствие (>90% в рабочий день)
        if (record.date in self.mass_absence_dates and record.is_workday):
            issues.append("День массового отсутствия (>90% отсутствуют)")
            return issues  # Остальное не проверяем
        
        # Если нет записей - это не технический сбой, просто отсутствие
        if entries is None or record.appearances == 0:
            return issues
        
        # === Проверки для случаев с записями ===
        
        # 3. Ночная активность (только в рабочие дни - аномалия времени)
        # Проверяем время ПРИХОДА и УХОДА, а не все промежуточные записи
        if (record.is_workday and
                TimeValidator.has_night_activity(
                    record.arrival_time,
                    record.departure_time)):
            issues.append("Ночная активность")

        # 4. Одно появление (камера не зафиксировала приход ИЛИ уход)
        # Проверяем только для рабочих дней
        if record.is_workday and record.appearances == 1:
            issues.append("Одно появление")
        
        # 5. Экстремальное опоздание (>3 часа = вероятно сбой)
        if (record.is_late and
                TimeValidator.is_extreme_late(record.late_minutes)):
            hours = record.late_minutes // 60
            minutes = record.late_minutes % 60
            issues.append(f"Экстремальное опоздание ({hours}ч {minutes}м)")

        # 6. Критическая недоработка (<7ч или на 2+ч меньше)
        # Проверяем только для рабочих дней
        if (record.is_workday and
            TimeValidator.is_critical_underwork(
                record.work_hours, record.expected_hours)):
            issues.append(
                f"Критическая недоработка ({record.work_hours:.1f}ч)"
            )
        
        return issues
