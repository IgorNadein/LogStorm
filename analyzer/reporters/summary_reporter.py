#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Репортер текстовых сводок
"""

import pandas as pd
from typing import List
from core.models import AttendanceRecord
from analyzer.status import StatusAnalyzer
from core.settings import TOP_N_USERS, OVERTIME_THRESHOLD


class SummaryReporter:
    """
    Генерация текстовых сводок
    
    Выводит статистику в консоль:
    - Общая статистика
    - Опоздания
    - Переработки
    - Технические сбои
    """
    
    def __init__(self, records: List[AttendanceRecord]):
        """
        Args:
            records: Список записей посещаемости
        """
        self.records = records
        # Фильтруем только валидные записи (БЕЗ технических сбоев)
        self.valid_records = [
            r for r in records
            if StatusAnalyzer.should_count_in_summary(r, 'hours')
        ]
    
    def print_summary(self):
        """Вывод полной сводки в консоль"""
        print("\n" + "="*80)
        print("СВОДКА ПО АНАЛИЗУ ПОСЕЩАЕМОСТИ")
        print("="*80)
        
        self._print_general_stats()
        self._print_late_stats()
        self._print_underwork_stats()
        self._print_overtime_stats()
        self._print_work_hours_stats()
        self._print_employee_issues()
        self._print_technical_issues()
        
        print("\n" + "="*80)
    
    def _print_general_stats(self):
        """Общая статистика"""
        total = len(self.records)
        valid = len(self.valid_records)
        technical = len([r for r in self.records if r.has_technical_issues])
        
        # Уникальные пользователи и даты
        unique_users = len(set(r.user_name for r in self.records))
        unique_dates = len(set(r.date for r in self.records))
        
        print(f"\n[ОБЩАЯ СТАТИСТИКА]")
        print(f"  • Всего записей: {total}")
        print(f"  • Валидных записей: {valid} ({valid/total*100:.1f}%)")
        print(f"  • Технических сбоев системы: {technical}")
        print(f"  • Уникальных пользователей: {unique_users}")
        print(f"  • Дней в отчете: {unique_dates}")
    
    def _print_late_stats(self):
        """Статистика по опозданиям"""
        # ИСПРАВЛЕН БАГ: только валидные записи!
        late_records = [
            r for r in self.valid_records
            if r.is_late and StatusAnalyzer.should_count_in_summary(r, 'late')
        ]
        late_count = len(late_records)
        late_percent = (
            (late_count / len(self.valid_records) * 100)
            if self.valid_records else 0
        )
        
        print(f"\n[РЕАЛЬНЫЕ ОПОЗДАНИЯ СОТРУДНИКОВ]")
        print(f"  • Всего случаев: {late_count} ({late_percent:.1f}%)")
        
        if late_count > 0:
            avg_late = sum(r.late_minutes for r in late_records) / late_count
            max_late = max(r.late_minutes for r in late_records)
            print(f"  • Среднее опоздание: {avg_late:.0f} минут")
            print(f"  • Максимальное опоздание: {max_late:.0f} минут")
            
            # Топ опаздывающих
            late_by_user = {}
            for r in late_records:
                late_by_user[r.display_name] = late_by_user.get(r.display_name, 0) + 1
            
            top_late = sorted(late_by_user.items(), key=lambda x: x[1], reverse=True)
            print(f"  • Топ-{TOP_N_USERS} опаздывающих:")
            for name, count in top_late[:TOP_N_USERS]:
                print(f"    - {name}: {count} раз(а)")
    
    def _print_underwork_stats(self):
        """Статистика по недоработкам"""
        # Только валидные записи (рабочие дни)
        underwork_records = [
            r for r in self.valid_records
            if r.is_underwork and r.is_workday
        ]
        underwork_count = len(underwork_records)
        underwork_percent = (
            (underwork_count / len(self.valid_records) * 100)
            if self.valid_records else 0
        )
        
        print(f"\n[НЕДОРАБОТКИ (отработано меньше нормы)]:")
        print(f"  • Всего случаев: {underwork_count} ({underwork_percent:.1f}%)")
        
        if underwork_count > 0:
            avg_deficit = sum(
                r.expected_hours - r.work_hours 
                for r in underwork_records
            ) / underwork_count
            print(f"  • Средний дефицит: {avg_deficit:.2f} часов")
            
            # Топ по недоработкам
            underwork_by_user = {}
            for r in underwork_records:
                underwork_by_user[r.display_name] = underwork_by_user.get(r.display_name, 0) + 1
            
            top_underwork = sorted(underwork_by_user.items(), key=lambda x: x[1], reverse=True)
            print(f"  • Топ-{TOP_N_USERS} по недоработкам:")
            for name, count in top_underwork[:TOP_N_USERS]:
                print(f"    - {name}: {count} раз(а)")
    
    def _print_overtime_stats(self):
        """Статистика по переработкам"""
        # ИСПРАВЛЕН БАГ: только валидные записи!
        overtime_records = [
            r for r in self.valid_records
            if r.is_overtime and StatusAnalyzer.should_count_in_summary(r, 'overtime')
        ]
        overtime_count = len(overtime_records)
        overtime_percent = (
            (overtime_count / len(self.valid_records) * 100)
            if self.valid_records else 0
        )
        
        print(f"\n[ПЕРЕРАБОТКИ (>{OVERTIME_THRESHOLD} часов)]:")
        print(f"  • Всего случаев: {overtime_count} ({overtime_percent:.1f}%)")
        
        if overtime_count > 0:
            # Топ по переработкам
            overtime_by_user = {}
            for r in overtime_records:
                overtime_by_user[r.display_name] = overtime_by_user.get(r.display_name, 0) + 1
            
            top_overtime = sorted(overtime_by_user.items(), key=lambda x: x[1], reverse=True)
            print(f"  • Топ-{TOP_N_USERS} по переработкам:")
            for name, count in top_overtime[:TOP_N_USERS]:
                print(f"    - {name}: {count} раз(а)")
    
    def _print_work_hours_stats(self):
        """Статистика по рабочим часам"""
        if not self.valid_records:
            return
        
        avg_hours = sum(r.work_hours for r in self.valid_records) / len(self.valid_records)
        min_hours = min(r.work_hours for r in self.valid_records)
        max_hours = max(r.work_hours for r in self.valid_records)
        
        print(f"\n[РАБОЧИЕ ЧАСЫ (валидные записи)]:")
        print(f"  • Средняя продолжительность: {avg_hours:.2f} часов")
        print(f"  • Минимум: {min_hours:.2f} часов")
        print(f"  • Максимум: {max_hours:.2f} часов")
    
    def _print_employee_issues(self):
        """Проблемы сотрудников"""
        employee_issues_count = len([r for r in self.records if r.has_employee_issues])
        print(f"\n[ПРОБЛЕМЫ СОТРУДНИКОВ]:")
        print(f"  • Всего случаев с проблемами: {employee_issues_count}")
    
    def _print_technical_issues(self):
        """Технические сбои"""
        technical_records = [r for r in self.records if r.has_technical_issues]
        print(f"\n[ТЕХНИЧЕСКИЕ СБОИ СИСТЕМЫ]:")
        print(f"  • Всего подозрительных случаев: {len(technical_records)}")
        
        if technical_records and len(technical_records) <= 10:
            print(f"\n  Детали:")
            for r in technical_records[:10]:
                print(
                    f"    - {r.date} | {r.display_name}: "
                    f"{r.technical_issues_text}"
                )
            
            if len(technical_records) > 10:
                remaining = len(technical_records) - 10
                print(f"    ... и еще {remaining} случаев")
