#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Индекс для быстрого поиска сотрудников
Отвечает за разрешение aliases и поиск по имени
"""

from typing import Dict, List, Optional


class PersonIndex:
    """
    Индексирует маппинги сотрудников для быстрого поиска
    
    Строит следующие индексы:
    1. reverse_alias_map: {alias_id -> main_id} для разрешения aliases
    2. name_to_id_map: {normalized_name -> person_id} для поиска по имени
    """
    
    def __init__(self, mappings: Dict, aliases: Dict):
        """
        Args:
            mappings: Словарь маппингов {person_id: {...}}
            aliases: Словарь aliases {main_id: [alias_id1, alias_id2, ...]}
        """
        self.mappings = mappings
        self.aliases = aliases
        self.reverse_alias_map = {}  # alias -> main_id
        self.name_to_id_map = {}     # normalized_name -> person_id
        
        self._build_indexes()
    
    def _build_indexes(self):
        """Построение индексов для быстрого поиска"""
        # Индекс: alias -> main_id
        for main_id, alias_list in self.aliases.items():
            if isinstance(alias_list, list):
                for alias in alias_list:
                    self.reverse_alias_map[alias] = main_id
        
        # Индекс: имя -> person_id
        for person_id, person_data in self.mappings.items():
            original_names = person_data.get('original_names', [])
            for name in original_names:
                normalized_name = self._normalize_name(name)
                self.name_to_id_map[normalized_name] = person_id
    
    @staticmethod
    def _normalize_name(name: str) -> str:
        """Нормализация имени (убирает лишние пробелы)"""
        return ' '.join(name.split())
    
    def resolve_person_id(self, employee_id: str, name: Optional[str] = None) -> str:
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
            normalized_name = self._normalize_name(name)
            if normalized_name in self.name_to_id_map:
                return self.name_to_id_map[normalized_name]
        
        # 4. Не нашли - возвращаем оригинальный ID
        return employee_id
    
    def get_display_name(self, person_id: str) -> str:
        """
        Получить отображаемое имя сотрудника
        
        Args:
            person_id: ID сотрудника (уже разрешённый)
            
        Returns:
            Отображаемое имя или сам ID
        """
        if person_id in self.mappings:
            return self.mappings[person_id].get('display_name', person_id)
        return person_id
    
    def get_all_person_ids(self) -> List[str]:
        """
        Получить список всех ID сотрудников (без aliases)
        
        Returns:
            Список главных ID
        """
        return list(self.mappings.keys())
    
    def add_person(self, person_id: str, display_name: str,
                   original_names: List[str]) -> None:
        """
        Добавить нового сотрудника в индекс
        
        Args:
            person_id: ID сотрудника
            display_name: Отображаемое имя
            original_names: Список возможных имён из СКУД
        """
        # Обновляем индекс имя -> ID
        for name in original_names:
            normalized_name = self._normalize_name(name)
            self.name_to_id_map[normalized_name] = person_id
    
    def add_alias(self, main_id: str, alias_ids: List[str]) -> None:
        """
        Добавить aliases в индекс
        
        Args:
            main_id: Главный ID
            alias_ids: Список дополнительных ID
        """
        self.aliases[main_id] = alias_ids
        
        # Обновляем обратный индекс
        for alias in alias_ids:
            self.reverse_alias_map[alias] = main_id
