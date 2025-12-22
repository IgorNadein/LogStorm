#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сервис маппинга сотрудников из системы СКУД
Позволяет:
1. Изменять имена сотрудников
2. Устанавливать индивидуальные расписания
3. Объединять несколько ID в одного человека (aliases)
"""

import json
from typing import Dict, Optional, List, Tuple


class PersonMapper:
    """Маппер для преобразования данных сотрудников из СКУД"""
    
    def __init__(self, mapping_file: str):
        """
        Args:
            mapping_file: Путь к JSON файлу с конфигурацией маппинга
        """
        self.mapping_file = mapping_file
        self.mappings = {}
        self.aliases = {}
        self.reverse_alias_map = {}  # Для быстрого поиска главного ID по алиасу
        self.name_to_id_map = {}  # Для поиска ID по имени из логов
        
        self._load_mappings()
    
    def _load_mappings(self):
        """Загрузка конфигурации маппинга"""
        try:
            with open(self.mapping_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            self.mappings = config.get('person_mappings', {})
            self.aliases = config.get('aliases', {})
            
            # Построение обратного индекса для aliases
            for main_id, alias_list in self.aliases.items():
                if isinstance(alias_list, list):
                    for alias in alias_list:
                        self.reverse_alias_map[alias] = main_id
            
            # Построение индекса имя -> ID
            for person_id, person_data in self.mappings.items():
                original_names = person_data.get('original_names', [])
                for name in original_names:
                    # Нормализуем имя (убираем лишние пробелы)
                    normalized_name = ' '.join(name.split())
                    self.name_to_id_map[normalized_name] = person_id
            
            print(f"✅ Загружено {len(self.mappings)} маппингов сотрудников")
            if self.aliases:
                print(f"✅ Загружено {len(self.aliases)} групп aliases")
                
        except FileNotFoundError:
            print(f"⚠️ Файл маппинга {self.mapping_file} не найден")
        except json.JSONDecodeError as e:
            print(f"❌ Ошибка парсинга JSON: {e}")
    
    def resolve_person_id(self, employee_id: str, name: str = None) -> str:
        """
        Определяет главный ID сотрудника с учётом aliases
        
        Args:
            employee_id: ID из СКУД (employeeNoString)
            name: Имя из СКУД (опционально, для поиска по имени)
            
        Returns:
            Главный ID сотрудника
        """
        # 1. Проверяем, является ли ID алиасом
        if employee_id in self.reverse_alias_map:
            return self.reverse_alias_map[employee_id]
        
        # 2. Если ID есть в маппинге - возвращаем его
        if employee_id in self.mappings:
            return employee_id
        
        # 3. Пытаемся найти по имени
        if name:
            normalized_name = ' '.join(name.split())
            if normalized_name in self.name_to_id_map:
                return self.name_to_id_map[normalized_name]
        
        # 4. Не нашли - возвращаем оригинальный ID
        return employee_id
    
    def get_display_name(self, person_id: str) -> str:
        """
        Получить отображаемое имя сотрудника
        
        Args:
            person_id: ID сотрудника (уже разрешённый через resolve_person_id)
            
        Returns:
            Отображаемое имя или сам ID, если маппинг не найден
        """
        if person_id in self.mappings:
            return self.mappings[person_id].get('display_name', person_id)
        return person_id
    
    def get_schedule(self, person_id: str) -> Dict:
        """
        Получить расписание сотрудника
        
        Args:
            person_id: ID сотрудника
            
        Returns:
            Словарь с параметрами расписания:
            - workdays: список рабочих дней
            - start_time: время начала
            - end_time: время окончания
            - work_hours: часов работы
        """
        default_schedule = {
            'workdays': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
            'start_time': '09:00',
            'end_time': '18:00',
            'work_hours': 9
        }
        
        if person_id not in self.mappings:
            return default_schedule
        
        person_data = self.mappings[person_id]
        
        return {
            'workdays': person_data.get('workdays', default_schedule['workdays']),
            'start_time': person_data.get('start_time', default_schedule['start_time']),
            'end_time': person_data.get('end_time', default_schedule['end_time']),
            'work_hours': person_data.get('work_hours', default_schedule['work_hours'])
        }
    
    def process_event(self, event: Dict) -> Tuple[str, str]:
        """
        Обработка события из СКУД: определение ID и имени сотрудника
        
        Args:
            event: Словарь с данными события (строка из NDJSON)
            
        Returns:
            Кортеж (person_id, display_name)
        """
        # Извлекаем ID и имя из события
        employee_id = event.get('employeeNoString', '')
        name = event.get('name', '')
        
        # Если нет ID - пытаемся использовать cardNo
        if not employee_id:
            card_no = event.get('cardNo', '')
            if card_no and card_no != '0':
                employee_id = str(card_no)
        
        # Если всё ещё нет ID - используем имя
        if not employee_id:
            employee_id = name if name else 'unknown'
        
        # Разрешаем главный ID (с учётом aliases)
        person_id = self.resolve_person_id(employee_id, name)
        
        # Получаем отображаемое имя
        display_name = self.get_display_name(person_id)
        
        return person_id, display_name
    
    def get_all_person_ids(self) -> List[str]:
        """
        Получить список всех ID сотрудников (без aliases)
        
        Returns:
            Список главных ID всех сотрудников
        """
        return list(self.mappings.keys())
    
    def convert_to_prefs_format(self) -> Dict:
        """
        Конвертировать маппинг в формат person_prefs.json для совместимости
        
        Returns:
            Словарь в формате {person_id: {display_name, workdays, start_time, ...}}
        """
        prefs = {}
        
        for person_id, person_data in self.mappings.items():
            prefs[person_id] = {
                'display_name': person_data.get('display_name', person_id),
                'workdays': person_data.get('workdays', 
                    ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']),
                'start_time': person_data.get('start_time', '09:00'),
                'end_time': person_data.get('end_time', '18:00'),
                'work_hours': person_data.get('work_hours', 9)
            }
        
        return prefs
    
    def add_person(self, person_id: str, display_name: str, 
                   original_names: List[str] = None,
                   workdays: List[str] = None,
                   start_time: str = '09:00',
                   end_time: str = '18:00',
                   work_hours: int = 9) -> bool:
        """
        Добавить нового сотрудника в маппинг
        
        Args:
            person_id: ID сотрудника
            display_name: Отображаемое имя
            original_names: Список возможных имён из СКУД
            workdays: Рабочие дни
            start_time: Время начала работы
            end_time: Время окончания работы
            work_hours: Часов работы в день
            
        Returns:
            True если успешно добавлено
        """
        if original_names is None:
            original_names = [display_name]
        
        if workdays is None:
            workdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        
        self.mappings[person_id] = {
            'display_name': display_name,
            'original_names': original_names,
            'workdays': workdays,
            'start_time': start_time,
            'end_time': end_time,
            'work_hours': work_hours
        }
        
        # Обновляем индекс имя -> ID
        for name in original_names:
            normalized_name = ' '.join(name.split())
            self.name_to_id_map[normalized_name] = person_id
        
        return True
    
    def add_alias(self, main_id: str, alias_ids: List[str]) -> bool:
        """
        Добавить aliases для объединения нескольких ID в одного человека
        
        Args:
            main_id: Главный ID
            alias_ids: Список дополнительных ID
            
        Returns:
            True если успешно
        """
        self.aliases[main_id] = alias_ids
        
        # Обновляем обратный индекс
        for alias in alias_ids:
            self.reverse_alias_map[alias] = main_id
        
        return True
    
    def save_mappings(self) -> bool:
        """
        Сохранить текущие маппинги в файл
        
        Returns:
            True если успешно сохранено
        """
        try:
            config = {
                'README': 'Конфигурация для маппинга сотрудников из системы СКУД',
                'person_mappings': self.mappings,
                'aliases': {
                    'NOTE': 'Объединение нескольких ID в одного человека. '
                            'Ключ - главный ID, значение - список дополнительных ID',
                    **self.aliases
                }
            }
            
            with open(self.mapping_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Маппинг сохранён в {self.mapping_file}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка сохранения маппинга: {e}")
            return False
