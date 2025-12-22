#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сервис AI анализа через GigaChat
"""

import os
from datetime import datetime
from typing import List
from models import AttendanceRecord
from config import (
    OUTPUT_AI_SUMMARY_FILE,
    GIGACHAT_SCOPE,
    AI_PROMPT_SENTENCES
)

# GigaChat импорт (опционально)
try:
    from gigachat import GigaChat
    GIGACHAT_AVAILABLE = True
except ImportError:
    GIGACHAT_AVAILABLE = False


class AIService:
    """Сервис AI анализа посещаемости через GigaChat"""
    
    def __init__(self, records: List[AttendanceRecord]):
        """
        Args:
            records: Список записей посещаемости
        """
        self.records = records
        self.valid_records = [r for r in records if r.is_valid_record]
    
    def generate_summary(self):
        """Генерация AI-описания через GigaChat API"""
        print("\n[AI АНАЛИЗ]:")
        
        if not GIGACHAT_AVAILABLE:
            print("  ! GigaChat не установлен")
            print("  Для включения AI анализа выполните:")
            print("  pip install gigachat")
            return
        
        # Проверка наличия API ключа
        api_key = os.environ.get('GIGACHAT_API_KEY')
        if not api_key:
            print("  ! Не найден API ключ GigaChat")
            print("\n  📝 Настройка:")
            print("  1. Скопируйте файл .env.example в .env")
            print("  2. Откройте .env и вставьте ваш API ключ")
            print("  3. Запустите скрипт снова")
            print("\n  Или установите переменную окружения:")
            print("  export GIGACHAT_API_KEY='ваш_ключ'  # Linux/Mac")
            print("  set GIGACHAT_API_KEY=ваш_ключ     # Windows")
            print("\n  🔑 Получить ключ: https://developers.sber.ru/gigachat")
            print("  📚 Инструкция: см. файл GIGACHAT_SETUP.md")
            return
        
        try:
            # Подготовка статистики
            stats = self._prepare_statistics()
            prompt = self._build_prompt(stats)
            
            print("  Отправка запроса в GigaChat...")
            
            # Инициализация GigaChat
            with GigaChat(credentials=api_key, verify_ssl_certs=False) as giga:
                response = giga.chat(prompt)
                ai_summary = response.choices[0].message.content
            
            print("\n" + "="*80)
            print(ai_summary)
            print("="*80)
            
            # Сохранение в файл
            with open(OUTPUT_AI_SUMMARY_FILE, 'w', encoding='utf-8') as f:
                f.write("AI АНАЛИЗ ПОСЕЩАЕМОСТИ\n")
                f.write("="*80 + "\n\n")
                f.write(ai_summary)
                f.write("\n\n" + "="*80 + "\n")
                f.write(
                    f"Дата генерации: "
                    f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                )
            
            print(f"\n[OK] AI анализ сохранен в файл: {OUTPUT_AI_SUMMARY_FILE}")
            
        except Exception as e:
            print(f"  [X] Ошибка при обращении к GigaChat API: {e}")
            print("  Проверьте:")
            print("  1. Правильность API ключа")
            print("  2. Подключение к интернету")
            print("  3. Актуальность библиотеки gigachat")
    
    def _prepare_statistics(self) -> dict:
        """Подготовка статистики для промпта"""
        total_records = len(self.records)
        valid_records = len(self.valid_records)
        technical_issues = len([r for r in self.records if r.has_technical_issues])
        
        # Реальные опоздания (только валидные записи)
        late_records = [r for r in self.valid_records if r.is_late]
        late_count = len(late_records)
        
        # Переработки (только валидные записи)
        overtime_records = [r for r in self.valid_records if r.is_overtime]
        overtime_count = len(overtime_records)
        
        # Проблемы сотрудников
        employee_problems = len([r for r in self.records if r.has_employee_issues])
        
        # Средние рабочие часы
        avg_hours = (
            sum(r.work_hours for r in self.valid_records) / len(self.valid_records)
            if self.valid_records else 0
        )
        
        return {
            'total_records': total_records,
            'valid_records': valid_records,
            'valid_percent': (valid_records / total_records * 100) if total_records > 0 else 0,
            'technical_issues': technical_issues,
            'late_count': late_count,
            'late_percent': (late_count / valid_records * 100) if valid_records > 0 else 0,
            'overtime_count': overtime_count,
            'overtime_percent': (overtime_count / valid_records * 100) if valid_records > 0 else 0,
            'employee_problems': employee_problems,
            'avg_hours': avg_hours
        }
    
    def _build_prompt(self, stats: dict) -> str:
        """Построение промпта для GigaChat"""
        prompt = f"""Проанализируй данные посещаемости сотрудников и составь краткую профессиональную сводку.

ВАЖНО: Статистика очищена от технических сбоев системы. Учитываются только реальные проблемы сотрудников.

Статистика:
- Всего записей: {stats['total_records']}
- Валидных записей: {stats['valid_records']} ({stats['valid_percent']:.1f}%)
- Технических сбоев системы: {stats['technical_issues']} (не учитываются в статистике сотрудников)
- Реальных опозданий: {stats['late_count']} ({stats['late_percent']:.1f}% от валидных)
- Переработок: {stats['overtime_count']} ({stats['overtime_percent']:.1f}% от валидных)
- Реальных проблем сотрудников: {stats['employee_problems']}
- Средняя продолжительность рабочего дня: {stats['avg_hours']:.2f} часов

Составь сводку на 4-5 предложений:
1. Общая оценка дисциплины (на основе валидных данных)
2. Ключевые проблемы сотрудников (если есть)
3. Позитивные моменты
4. Краткие рекомендации
5. Оценка качества работы системы учета (если много технических сбоев)

Ответь кратко и по делу, без воды."""
        
        return prompt
