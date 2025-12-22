#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Маппер событий СКУД (Hikvision/HiWatch)
Классификация событий по major/minor кодам
"""


class EventMapper:
    """Маппинг событий контроля доступа"""
    
    # Карта событий: (major, minor) -> (type, description)
    EVENT_MAP = {
        # Успешные проходы
        (5, 75): ("pass_in", "Успешный вход"),
        (5, 104): ("pass_out", "Успешный выход"),
        
        # Дверь
        (5, 21): ("door_open", "Дверь открыта"),
        (5, 22): ("door_close", "Дверь закрыта"),
        
        # Ошибки и аномалии
        (5, 76): ("unknown_face", "Неопознанное лицо"),
        (5, 77): ("card_expired", "Карта просрочена"),
        (5, 78): ("invalid_card", "Недействительная карта"),
        (5, 79): ("blacklist", "Карта в черном списке"),
        
        # Дополнительные события
        (5, 0): ("general_event", "Общее событие"),
    }
    
    @classmethod
    def get_event_type(cls, major: int, minor: int) -> str:
        """
        Получить тип события
        
        Args:
            major: Major код события
            minor: Minor код события
            
        Returns:
            Тип события (pass_in, pass_out, door_open, unknown_face и т.д.)
        """
        event_info = cls.EVENT_MAP.get((major, minor))
        if event_info:
            return event_info[0]
        return "unknown"
    
    @classmethod
    def get_event_description(cls, major: int, minor: int) -> str:
        """
        Получить описание события
        
        Args:
            major: Major код события
            minor: Minor код события
            
        Returns:
            Описание события на русском
        """
        event_info = cls.EVENT_MAP.get((major, minor))
        if event_info:
            return event_info[1]
        return f"Неизвестное событие ({major}/{minor})"
    
    @classmethod
    def is_valid_pass(cls, major: int, minor: int) -> bool:
        """
        Проверка, является ли событие валидным проходом
        
        Args:
            major: Major код события
            minor: Minor код события
            
        Returns:
            True если это успешный вход/выход
        """
        event_type = cls.get_event_type(major, minor)
        return event_type in ("pass_in", "pass_out")
    
    @classmethod
    def is_error_event(cls, major: int, minor: int) -> bool:
        """
        Проверка, является ли событие ошибкой
        
        Args:
            major: Major код события
            minor: Minor код события
            
        Returns:
            True если это ошибка (неопознанное лицо, карта и т.д.)
        """
        event_type = cls.get_event_type(major, minor)
        return event_type in (
            "unknown_face", "card_expired", "invalid_card", "blacklist"
        )
    
    @classmethod
    def get_all_pass_events(cls) -> list:
        """
        Получить список всех типов проходов
        
        Returns:
            Список кортежей [(major, minor), ...]
        """
        return [
            key for key, val in cls.EVENT_MAP.items()
            if val[0] in ("pass_in", "pass_out")
        ]
