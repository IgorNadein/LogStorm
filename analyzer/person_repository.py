#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Репозиторий для загрузки и сохранения маппинга сотрудников
Отвечает только за работу с JSON файлом
"""

import json
from typing import Dict, Tuple


class PersonRepository:
    """Репозиторий для работы с файлом маппинга сотрудников"""
    
    @staticmethod
    def load(file_path: str) -> Tuple[Dict, Dict]:
        """
        Загрузить маппинг из JSON файла
        
        Args:
            file_path: Путь к JSON файлу
            
        Returns:
            Кортеж (mappings, aliases):
            - mappings: словарь {person_id: {display_name, original_names, ...}}
            - aliases: словарь {main_id: [alias_id1, alias_id2, ...]}
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            mappings = config.get('person_mappings', {})
            aliases = config.get('aliases', {})
            
            # Очистка aliases от служебных полей
            if 'NOTE' in aliases:
                del aliases['NOTE']
            
            print(f"[OK] Загружено {len(mappings)} маппингов сотрудников")
            if aliases:
                print(f"[OK] Загружено {len(aliases)} групп aliases")
            
            return mappings, aliases
            
        except FileNotFoundError:
            print(f"[WARNING] Файл маппинга {file_path} не найден")
            return {}, {}
            
        except json.JSONDecodeError as e:
            print(f"[ERROR] Ошибка парсинга JSON: {e}")
            return {}, {}
    
    @staticmethod
    def save(file_path: str, mappings: Dict, aliases: Dict) -> bool:
        """
        Сохранить маппинг в JSON файл
        
        Args:
            file_path: Путь к JSON файлу
            mappings: Словарь маппингов сотрудников
            aliases: Словарь aliases
            
        Returns:
            True если успешно сохранено
        """
        try:
            config = {
                'README': 'Конфигурация для маппинга сотрудников из системы СКУД',
                'person_mappings': mappings,
                'aliases': {
                    'NOTE': 'Объединение нескольких ID в одного человека. '
                            'Ключ - главный ID, значение - список дополнительных ID',
                    **aliases
                }
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            print(f"[OK] Маппинг сохранён в {file_path}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Ошибка сохранения маппинга: {e}")
            return False
