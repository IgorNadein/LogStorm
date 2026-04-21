#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор Excel отчётов
"""

import pandas as pd
from typing import List
from core.models import AttendanceRecord
from analyzer.reporters.excel_formatter import ExcelFormatter
from config import (
    OUTPUT_EXCEL_FILE,
    SHEET_MAIN_REPORT,
    SHEET_SUSPICIOUS,
    MONTHS_RU
)


class ExcelReporter:
    """Генерация Excel отчётов из записей посещаемости"""
    
    def __init__(self, records: List[AttendanceRecord]):
        """
        Args:
            records: Список записей посещаемости
        """
        self.records = records
        self.monthly_status_data = {}  # Для форматирования месячных листов
    
    def generate_report(self, output_file: str = OUTPUT_EXCEL_FILE):
        """
        Генерация полного Excel отчёта
        
        Args:
            output_file: Путь к выходному файлу
        """
        print(f"Генерация Excel отчета: {output_file}")
        
        # Конвертация записей в DataFrame
        df = self._records_to_dataframe()
        
        # Создание Excel файла
        try:
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                # 1. Основной отчёт по дням
                df.to_excel(writer, sheet_name=SHEET_MAIN_REPORT, index=False)
                
                # 2. Подозрительные случаи (технические сбои)
                df_suspicious = df[df['Технический сбой'] != 'Нет']
                if not df_suspicious.empty:
                    df_suspicious.to_excel(
                        writer,
                        sheet_name=SHEET_SUSPICIOUS,
                        index=False
                    )
                
                # 3. Помесячные таблицы
                self._generate_monthly_sheets(writer, df)
        except PermissionError:
            print(f"\n[ОШИБКА] Файл {output_file} открыт в другой программе!")
            print("Закройте файл и запустите снова.\n")
            return False
        
        # Применяем форматирование (цвета, границы, ширину колонок)
        formatter = ExcelFormatter(output_file, self)
        formatter.format_all()
        
        print(f"Excel отчёт сохранён: {output_file}")
        return True
    
    def _records_to_dataframe(self) -> pd.DataFrame:
        """Конвертация списка AttendanceRecord в DataFrame"""
        data = [record.to_dict() for record in self.records]
        df = pd.DataFrame(data)
        # Сортировка по дате и имени
        df = df.sort_values(['Дата', 'Имя'])
        return df
    
    def _generate_monthly_sheets(self, writer, df: pd.DataFrame):
        """
        Генерация помесячных таблиц
        
        Создаёт отдельный лист для каждого месяца с таблицей:
        - Строки: пользователи
        - Столбцы: дни (2 колонки на день: приход/уход)
        - Итоговые колонки: статистика по пользователю
        """
        # Преобразуем даты
        df['Дата_dt'] = pd.to_datetime(df['Дата'])
        
        # Группируем по месяцам
        months = df['Дата_dt'].dt.to_period('M').unique()
        
        for month_period in sorted(months):
            month_data = df[df['Дата_dt'].dt.to_period('M') == month_period]
            
            if month_data.empty:
                continue
            
            # Название листа (без слова "месяц")
            month_name = MONTHS_RU[month_period.month]
            year = month_period.year
            sheet_name = f"{month_name} {year}"
            
            # Создаём таблицу
            df_month = self._create_monthly_table(month_data)
            
            # Записываем БЕЗ заголовков (добавим свои при форматировании)
            df_month.to_excel(
                writer,
                sheet_name=sheet_name,
                index=False,
                header=False,
                startrow=0
            )
    
    def _create_monthly_table(self, month_data: pd.DataFrame) -> pd.DataFrame:
        """Создание транспонированной таблицы (даты по вертикали)"""
        users = sorted(month_data['Имя'].unique())
        dates = sorted(month_data['Дата_dt'].dt.date.unique())
        
        # Словарь для хранения статусов (для форматирования)
        status_matrix = {}
        
        # Создаем таблицу: строки=даты, столбцы=пользователи
        matrix_data = []
        
        for date in dates:
            # Форматируем дату с днём недели
            from config import DAYS_RU
            weekday_en = pd.Timestamp(date).day_name()
            weekday_ru = DAYS_RU.get(weekday_en, weekday_en)
            date_str = f"{date.day} ({weekday_ru})"
            row = {'Дата': date_str}
            
            for user in users:
                day_data = month_data[
                    (month_data['Имя'] == user) & 
                    (month_data['Дата_dt'].dt.date == date)
                ]
                
                if not day_data.empty:
                    row[f"{user}_Приход"] = day_data.iloc[0]['Приход']
                    row[f"{user}_Уход"] = day_data.iloc[0]['Уход']
                    
                    # Сохраняем статус для форматирования
                    status_key = f"{date}_{user}"
                    status_matrix[status_key] = {
                        'late': day_data.iloc[0]['Опоздание'] == 'Да',
                        'early_leave': day_data.iloc[0]['Ранний уход'] == 'Да',
                        'underwork': day_data.iloc[0]['Недоработка часов'] == 'Да',
                        'overtime': day_data.iloc[0]['Переработка'] == 'Да',
                        'technical': day_data.iloc[0]['Технический сбой'] != 'Нет',
                        'is_workday': day_data.iloc[0]['Рабочий день'] == 'Да'
                    }
                else:
                    row[f"{user}_Приход"] = ''
                    row[f"{user}_Уход"] = ''
            
            matrix_data.append(row)
        
        # Добавляем итоговые строки
        summary_rows = []
        
        # Валидные РАБОЧИЕ дни (для корректного сравнения с опозданиями/уходами)
        row_valid = {'Дата': 'Учтено(дней)'}
        for user in users:
            user_data = month_data[month_data['Имя'] == user]
            # Только рабочие дни без технических сбоев
            valid_data = user_data[
                (user_data['Технический сбой'] == 'Нет') &
                (user_data['Рабочий день'] == 'Да')
            ]
            row_valid[f"{user}_Приход"] = len(valid_data)
            row_valid[f"{user}_Уход"] = ''
        summary_rows.append(row_valid)
        
        # Неучтенные дни (рабочие дни с техсбоями)
        row_invalid = {'Дата': 'Неучтено(дней)'}
        for user in users:
            user_data = month_data[month_data['Имя'] == user]
            workdays = user_data[user_data['Рабочий день'] == 'Да']
            invalid_count = len(workdays[workdays['Технический сбой'] != 'Нет'])
            row_invalid[f"{user}_Приход"] = invalid_count
            row_invalid[f"{user}_Уход"] = ''
        summary_rows.append(row_invalid)
        
        # Отработано часов (только рабочие дни без техсбоев)
        row_hours = {'Дата': 'Отработано(часов)'}
        for user in users:
            user_data = month_data[month_data['Имя'] == user]
            valid_data = user_data[
                (user_data['Технический сбой'] == 'Нет') &
                (user_data['Рабочий день'] == 'Да')
            ]
            total_hours = round(valid_data['Рабочих часов'].sum(), 2)
            row_hours[f"{user}_Приход"] = total_hours
            row_hours[f"{user}_Уход"] = ''
        summary_rows.append(row_hours)
        
        # Опоздания (только рабочие дни без техсбоев)
        row_late = {'Дата': 'Опозданий'}
        for user in users:
            user_data = month_data[month_data['Имя'] == user]
            valid_data = user_data[
                (user_data['Технический сбой'] == 'Нет') &
                (user_data['Рабочий день'] == 'Да')
            ]
            late_count = len(valid_data[valid_data['Опоздание'] == 'Да'])
            row_late[f"{user}_Приход"] = late_count
            row_late[f"{user}_Уход"] = ''
        summary_rows.append(row_late)
        
        # Ранние уходы (рабочие дни без техсбоев)
        row_early = {'Дата': 'Ранних уходов'}
        for user in users:
            user_data = month_data[month_data['Имя'] == user]
            valid_data = user_data[
                (user_data['Технический сбой'] == 'Нет') &
                (user_data['Рабочий день'] == 'Да')
            ]
            early_count = len(valid_data[valid_data['Ранний уход'] == 'Да'])
            row_early[f"{user}_Приход"] = early_count
            row_early[f"{user}_Уход"] = ''
        summary_rows.append(row_early)
        
        # Переработки (рабочие дни без техсбоев)
        row_overtime = {'Дата': 'Переработок'}
        for user in users:
            user_data = month_data[month_data['Имя'] == user]
            valid_data = user_data[
                (user_data['Технический сбой'] == 'Нет') &
                (user_data['Рабочий день'] == 'Да')
            ]
            overtime_count = len(valid_data[valid_data['Переработка'] == 'Да'])
            row_overtime[f"{user}_Приход"] = overtime_count
            row_overtime[f"{user}_Уход"] = ''
        summary_rows.append(row_overtime)
        
        # Отсутствия (рабочие дни, когда сотрудник не пришёл)
        row_absent = {'Дата': 'Отсутствий'}
        for user in users:
            user_data = month_data[month_data['Имя'] == user]
            # Отсутствие = рабочий день + нет прихода (Приход == '-')
            absent_count = len(user_data[
                (user_data['Рабочий день'] == 'Да') &
                (user_data['Приход'] == '-') &
                (user_data['Технический сбой'] == 'Нет')
            ])
            row_absent[f"{user}_Приход"] = absent_count
            row_absent[f"{user}_Уход"] = ''
        summary_rows.append(row_absent)
        
        # Объединяем данные и итоги
        all_data = matrix_data + summary_rows
        
        # Сохраняем для форматирования
        sheet_name = f"{MONTHS_RU[dates[0].month]} {dates[0].year}"
        self.monthly_status_data[sheet_name] = {
            'users': users,
            'dates': dates,
            'status_matrix': status_matrix,
            'summary_start_row': len(matrix_data)
        }
        
        # Создаём DataFrame
        df_month = pd.DataFrame(all_data)
        
        # Формируем порядок колонок: Дата + (User_Приход, User_Уход) для каждого
        user_columns = []
        for user in users:
            user_columns.append(f"{user}_Приход")
            user_columns.append(f"{user}_Уход")
        
        columns = ['Дата'] + user_columns
        return df_month[columns]
