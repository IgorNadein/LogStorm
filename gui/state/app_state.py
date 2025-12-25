"""
App State - управление состоянием приложения
"""

import json
from pathlib import Path
from typing import List, Dict
from config.colors import (
    ColorScheme,
    default_color_scheme,
    load_color_scheme_from_dict,
    save_color_scheme_to_dict
)


class AppState:
    """Класс для управления состоянием приложения"""
    
    def __init__(self):
        """Инициализация состояния"""
        self.files: List[str] = []
        self.verbose: bool = False
        self.df = None
        self.prefs: Dict = {}
        self.aliases: Dict = {}
        self.results = None
        self.prefs_file = Path("path/person_prefs.json")
        self.export_dir = Path("reports/")
        self.config_file = Path("config.json")
        
        # Источник данных (новое в v2.0)
        self.data_source_type: str = 'files'  # 'files' или 'sqlite'
        self.sqlite_path: str = ''
        self.filter_start_date = None  # Для фильтрации SQLite
        self.filter_end_date = None
        self.filter_devices = None
        
        # Цветовая схема (новое в v2.1)
        self.color_scheme: ColorScheme = default_color_scheme
        
        # Маппинг камер для прихода/ухода (новое в v2.2)
        self.device_mapping: Dict = None
    
    def load_prefs(self) -> bool:
        """
        Загрузить настройки сотрудников из файла
        
        Returns:
            bool: True если загрузка успешна
        """
        try:
            print(f"Загрузка prefs из: {self.prefs_file}")
            if self.prefs_file.exists():
                with open(self.prefs_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Проверяем что данные корректны
                if isinstance(data, dict):
                    # Новый формат: person_mapping.json
                    if 'person_mappings' in data:
                        self.prefs = data['person_mappings']
                        self.aliases = data.get('aliases', {})
                        print(f"Загружен новый формат: {len(self.prefs)} "
                              f"сотрудников, {len(self.aliases)} алиасов")
                        
                        # Валидация: убеждаемся что алиасы не дублируются
                        aliases_removed = 0
                        for main_id, alias_list in self.aliases.items():
                            if main_id == 'NOTE':
                                continue
                            if not isinstance(alias_list, list):
                                continue
                            # Проверяем что основной ID есть в prefs
                            if main_id not in self.prefs:
                                print(f"⚠️  Основной ID {main_id} "
                                      f"не найден в person_mappings!")
                            # Удаляем записи для алиасов
                            for alias_id in alias_list:
                                if alias_id in self.prefs:
                                    del self.prefs[alias_id]
                                    aliases_removed += 1
                        
                        if aliases_removed > 0:
                            print(f"✓ Убрано {aliases_removed} дублей "
                                  f"(осталось {len(self.prefs)} записей)")
                    # Старый формат: person_prefs.json
                    else:
                        self.prefs = data
                        self.aliases = {}
                        print("Загружен старый формат")
                    
                    return True
                else:
                    print(f"Некорректный формат prefs: {type(data)}")
            else:
                print(f"Файл не найден: {self.prefs_file}")
        except Exception as e:
            print(f"Ошибка загрузки prefs: {e}")
            import traceback
            traceback.print_exc()
        return False
    
    def save_prefs(self) -> bool:
        """
        Сохранить настройки сотрудников в файл
        
        Returns:
            bool: True если сохранение успешно
        """
        try:
            self.prefs_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Определяем формат: если есть aliases - новый формат
            if self.aliases:
                # Новый формат с aliases
                data = {
                    "README": "Конфигурация для маппинга сотрудников",
                    "person_mappings": self.prefs,
                    "aliases": self.aliases
                }
            else:
                # Старый формат (без aliases)
                data = self.prefs
            
            with open(self.prefs_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"✓ Prefs сохранены: {self.prefs_file}")
            print(f"  Сотрудников: {len(self.prefs)}, "
                  f"Алиасов: {len(self.aliases)}")
            return True
        except Exception as e:
            print(f"Ошибка сохранения prefs: {e}")
            import traceback
            traceback.print_exc()
        return False
    
    def get_persons_list(self) -> List[str]:
        """
        Получить список сотрудников для отображения
        
        Returns:
            List[str]: Список строк с информацией о сотрудниках
        """
        result = []
        for key, person_data in self.prefs.items():
            if isinstance(person_data, dict):
                display_name = person_data.get('display_name', key)
                result.append(f"{display_name} ({key})")
            else:
                # Если данные некорректны, просто показываем ключ
                result.append(f"{key} (некорректные данные)")
        return result
    
    def load_config(self) -> bool:
        """
        Загрузить конфигурацию приложения
        
        Returns:
            bool: True если загрузка успешна
        """
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # Загружаем источник данных
                data_source = config.get('data_source', {})
                self.data_source_type = data_source.get('type', 'files')
                self.sqlite_path = data_source.get('path', '')
                
                # Загружаем цветовую схему
                if 'color_scheme' in config:
                    self.color_scheme = load_color_scheme_from_dict(
                        config['color_scheme']
                    )
                
                # Загружаем маппинг камер
                self.device_mapping = config.get('device_mapping', None)
                
                self.files = config.get('files', [])
                self.verbose = config.get('verbose', False)
                
                # Проверяем путь к prefs_file
                prefs_path = config.get(
                    'prefs_file', 'path/person_prefs.json'
                )
                if prefs_path and prefs_path != '.':
                    self.prefs_file = Path(prefs_path)
                else:
                    self.prefs_file = Path('path/person_prefs.json')
                
                # Проверяем путь к export_dir
                export_path = config.get('export_dir', 'reports/')
                if export_path and export_path != '.':
                    self.export_dir = Path(export_path)
                else:
                    self.export_dir = Path('reports/')
                
                return True
        except Exception as e:
            print(f"Ошибка загрузки конфигурации: {e}")
        return False
    
    def save_config(self) -> bool:
        """
        Сохранить конфигурацию приложения
        
        Returns:
            bool: True если сохранение успешно
        """
        try:
            config = {
                'data_source': {
                    'type': self.data_source_type,
                    'path': (
                        self.sqlite_path
                        if self.data_source_type == 'sqlite'
                        else None
                    )
                },
                'color_scheme': save_color_scheme_to_dict(
                    self.color_scheme
                ),
                'device_mapping': self.device_mapping,
                'files': self.files,
                'verbose': self.verbose,
                'prefs_file': str(self.prefs_file),
                'export_dir': str(self.export_dir)
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Ошибка сохранения конфигурации: {e}")
        return False
