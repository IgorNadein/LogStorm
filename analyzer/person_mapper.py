#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сервис маппинга сотрудников из системы СКУД
Позволяет:
1. Изменять имена сотрудников
2. Устанавливать индивидуальные расписания
3. Объединять несколько ID в одного человека (aliases)

После рефакторинга: фасад над PersonRepository и PersonIndex
"""

from typing import Dict, List, Optional
from config import DEFAULT_SCHEDULE
from core.models import WorkSchedule
from .person_repository import PersonRepository
from .person_index import PersonIndex


class PersonMapper:
    """
    Маппер для преобразования данных сотрудников из СКУД
    
    Использует:
    - PersonRepository: загрузка/сохранение JSON
    - PersonIndex: индексирование и поиск
    """
    
    def __init__(self, mapping_file: str):
        """
        Args:
            mapping_file: Путь к JSON файлу с конфигурацией маппинга
        """
        self.mapping_file = mapping_file
        
        # Загружаем данные через Repository
        mappings, aliases = PersonRepository.load(mapping_file)
        
        # Строим индекс для быстрого поиска
        self.index = PersonIndex(mappings, aliases)
        
        # Сохраняем ссылку на mappings для get_schedule
        self.mappings = mappings
        self.aliases = aliases
    
    def resolve_person_id(self, employee_id: str, name: Optional[str] = None) -> str:
        """
        Определяет главный ID сотрудника с учётом aliases
        
        Args:
            employee_id: ID из СКУД (employeeNoString)
            name: Имя из СКУД (опционально, для поиска по имени)
            
        Returns:
            Главный ID сотрудника
        """
        return self.index.resolve_person_id(employee_id, name)
    
    def get_display_name(self, person_id: str) -> str:
        """
        Получить отображаемое имя сотрудника
        
        Args:
            person_id: ID сотрудника (уже разрешённый через resolve_person_id)
            
        Returns:
            Отображаемое имя или сам ID, если маппинг не найден
        """
        return self.index.get_display_name(person_id)
    
    def get_schedule(self, person_id: str) -> WorkSchedule:
        """
        Получить расписание сотрудника
        
        Args:
            person_id: ID сотрудника
            
        Returns:
            Объект WorkSchedule с параметрами расписания
        """
        if person_id not in self.mappings:
            # Возвращаем дефолтное расписание
            return WorkSchedule(
                start_time=DEFAULT_SCHEDULE['start_time'],
                end_time=DEFAULT_SCHEDULE['end_time'],
                workdays=DEFAULT_SCHEDULE['workdays'],
                expected_hours=DEFAULT_SCHEDULE['work_hours']
            )
        
        person_data = self.mappings[person_id]
        
        return WorkSchedule(
            start_time=person_data.get('start_time', DEFAULT_SCHEDULE['start_time']),
            end_time=person_data.get('end_time', DEFAULT_SCHEDULE['end_time']),
            workdays=person_data.get('workdays', DEFAULT_SCHEDULE['workdays']),
            expected_hours=person_data.get('work_hours', DEFAULT_SCHEDULE['work_hours'])
        )
    
    def get_all_person_ids(self) -> List[str]:
        """
        Получить список всех ID сотрудников (без aliases)
        
        Returns:
            Список главных ID всех сотрудников
        """
        return self.index.get_all_person_ids()
    
    def add_person(self, person_id: str, display_name: str, 
                   original_names: Optional[List[str]] = None,
                   schedule: Optional[WorkSchedule] = None) -> bool:
        """
        Добавить нового сотрудника в маппинг
        
        Args:
            person_id: ID сотрудника
            display_name: Отображаемое имя
            original_names: Список возможных имён из СКУД
            schedule: Расписание работы (WorkSchedule)
            
        Returns:
            True если успешно добавлено
        """
        if original_names is None:
            original_names = [display_name]
        
        if schedule is None:
            schedule = WorkSchedule(
                start_time=DEFAULT_SCHEDULE['start_time'],
                end_time=DEFAULT_SCHEDULE['end_time'],
                workdays=DEFAULT_SCHEDULE['workdays'],
                expected_hours=DEFAULT_SCHEDULE['work_hours']
            )
        
        self.mappings[person_id] = {
            'display_name': display_name,
            'original_names': original_names,
            'workdays': schedule.workdays,
            'start_time': schedule.start_time,
            'end_time': schedule.end_time,
            'work_hours': schedule.expected_hours
        }
        
        # Обновляем индекс
        self.index.add_person(person_id, display_name, original_names)
        
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
        # Обновляем индекс
        self.index.add_alias(main_id, alias_ids)
        return True
    
    def save_mappings(self) -> bool:
        """
        Сохранить текущие маппинги в файл
        
        Returns:
            True если успешно сохранено
        """
        return PersonRepository.save(
            self.mapping_file,
            self.mappings,
            self.aliases
        )
    
    def convert_to_prefs_format(self) -> Dict:
        """
        Конвертировать маппинг в старый формат person_prefs.json
        (для совместимости с существующим кодом)
        
        Returns:
            Словарь {person_id: {display_name, workdays, start_time, ...}}
        """
        prefs = {}
        
        for person_id, person_data in self.mappings.items():
            prefs[person_id] = {
                'display_name': person_data.get('display_name', person_id),
                'workdays': person_data.get('workdays',
                    DEFAULT_SCHEDULE['workdays']),
                'start_time': person_data.get('start_time',
                    DEFAULT_SCHEDULE['start_time']),
                'end_time': person_data.get('end_time',
                    DEFAULT_SCHEDULE['end_time']),
                'work_hours': person_data.get('work_hours',
                    DEFAULT_SCHEDULE['work_hours'])
            }
        
        return prefs
