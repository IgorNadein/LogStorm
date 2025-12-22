"""
LogStorm GUI - Fluent Design (Windows 11 Native Look)
"""

import sys
import json
from pathlib import Path
from typing import List, Optional, Dict

from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFileDialog,
    QMessageBox
)

# Импорт бэкенда
from services.data_loader import DataLoader
from services.attendance_service import AttendanceService
from services.ai_service import AIService
from services.person_mapper import PersonMapper
from reporters.excel_reporter import ExcelReporter

from qfluentwidgets import (
    FluentWindow, FluentIcon, NavigationItemPosition, setTheme, Theme,
    PrimaryPushButton, PushButton, ListWidget, CheckBox,
    StrongBodyLabel, BodyLabel, CardWidget, InfoBar, InfoBarPosition,
    LineEdit, ComboBox, MessageBox, ProgressRing, IndeterminateProgressBar,
    TableWidget, setThemeColor
)
from PySide6.QtWidgets import (
    QDialog, QLabel, QFormLayout, QTableWidgetItem, QHeaderView
)


class AnalysisWorker(QThread):
    """Рабочий поток для анализа"""
    finished = Signal(list)
    error = Signal(str)
    progress = Signal(str)
    
    def  __init__(self, files, prefs, use_ai=False, prefs_file=None):
        super().__init__()
        self.files = files
        self.prefs = prefs
        self.use_ai = use_ai
        self.prefs_file = prefs_file
    
    def run(self):
        """Выполнить анализ"""
        try:
            # Создаём PersonMapper если есть файл с алиасами
            person_mapper = None
            if self.prefs_file and Path(self.prefs_file).exists():
                self.progress.emit("Инициализация маппера сотрудников...")
                person_mapper = PersonMapper(str(self.prefs_file))
            
            # Загрузка данных с учётом алиасов
            self.progress.emit("Загрузка файлов...")
            df = DataLoader.load_logs(self.files, person_mapper=person_mapper)
            
            # Анализ посещаемости
            self.progress.emit("Анализ посещаемости...")
            service = AttendanceService(df, self.prefs)
            results = service.analyze_all()
            
            # AI обработка если включена
            if self.use_ai:
                self.progress.emit("AI анализ отсутствий...")
                try:
                    ai_service = AIService()
                    results = ai_service.enhance_results(results)
                except Exception as e:
                    print(f"AI анализ недоступен: {e}")
            
            self.progress.emit("Готово!")
            self.finished.emit(results)
            
        except Exception as e:
            import traceback
            error_details = f"{str(e)}\n{traceback.format_exc()}"
            print(f"ОШИБКА АНАЛИЗА:\n{error_details}")
            self.error.emit(str(e))


class PersonDialog(QDialog):
    """Диалог добавления/редактирования сотрудника"""
    
    def __init__(self, person_id=None, person_data=None, parent=None):
        super().__init__(parent)
        self.person_id = person_id
        self.person_data = person_data or {}
        
        self.setWindowTitle(
            "Редактировать сотрудника" if person_id 
            else "Добавить сотрудника"
        )
        self.resize(500, 400)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Карточка с формой
        card = CardWidget(self)
        form_layout = QFormLayout(card)
        form_layout.setSpacing(12)
        
        # ID сотрудника
        self.id_edit = LineEdit(self)
        self.id_edit.setPlaceholderText("ivan_ivanov")
        if person_id:
            self.id_edit.setText(person_id)
            self.id_edit.setReadOnly(True)
        form_layout.addRow(QLabel("ID:"), self.id_edit)
        
        # Отображаемое имя
        self.name_edit = LineEdit(self)
        self.name_edit.setPlaceholderText("Employee Sample")
        self.name_edit.setText(
            self.person_data.get('display_name', '')
        )
        form_layout.addRow(QLabel("Имя:"), self.name_edit)
        
        # Время начала работы
        self.start_time_edit = LineEdit(self)
        self.start_time_edit.setPlaceholderText("09:00")
        self.start_time_edit.setText(
            self.person_data.get('start_time', '')
        )
        form_layout.addRow(QLabel("Начало работы:"), self.start_time_edit)
        
        # Рабочие дни
        self.workdays_edit = LineEdit(self)
        self.workdays_edit.setPlaceholderText(
            "Monday, Tuesday, Wednesday, Thursday, Friday"
        )
        workdays = self.person_data.get('workdays', [])
        if workdays:
            self.workdays_edit.setText(", ".join(workdays))
        form_layout.addRow(QLabel("Рабочие дни:"), self.workdays_edit)
        
        # Алиасы (дополнительные ID)
        self.aliases_edit = LineEdit(self)
        self.aliases_edit.setPlaceholderText("123, 456, 789 (через запятую)")
        aliases = self.person_data.get('_aliases', [])
        if aliases:
            self.aliases_edit.setText(", ".join(str(a) for a in aliases))
        form_layout.addRow(QLabel("Алиасы (доп. ID):"), self.aliases_edit)
        
        layout.addWidget(card)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)
        
        self.save_btn = PrimaryPushButton("Сохранить", self)
        self.save_btn.clicked.connect(self.accept)
        
        self.cancel_btn = PushButton("Отмена", self)
        self.cancel_btn.clicked.connect(self.reject)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.cancel_btn)
        buttons_layout.addWidget(self.save_btn)
        
        layout.addLayout(buttons_layout)
    
    def get_person_data(self):
        """Получить данные сотрудника"""
        data = {
            'display_name': self.name_edit.text().strip()
        }
        
        # Добавляем start_time если указан
        start_time = self.start_time_edit.text().strip()
        if start_time:
            data['start_time'] = start_time
        
        # Добавляем workdays если указаны
        workdays_text = self.workdays_edit.text().strip()
        if workdays_text:
            workdays = [day.strip() for day in workdays_text.split(',')]
            data['workdays'] = workdays
        
        # Добавляем алиасы если указаны
        aliases_text = self.aliases_edit.text().strip()
        if aliases_text:
            aliases = [aid.strip() for aid in aliases_text.split(',') if aid.strip()]
            data['_aliases'] = aliases
        
        return self.id_edit.text().strip(), data


class AppState:
    """Состояние приложения"""
    def __init__(self):
        self.files: List[str] = []
        self.use_ai: bool = True
        self.verbose: bool = False
        self.df = None
        self.prefs: Dict = {}
        self.aliases: Dict = {}
        self.results = None
        self.prefs_file = Path("path/person_prefs.json")
        self.export_dir = Path("reports/")
        self.config_file = Path("config.json")
        
    def load_prefs(self) -> bool:
        """Загрузить настройки сотрудников"""
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
                            # Удаляем записи для алиасов (чтобы избежать дублей)
                            for alias_id in alias_list:
                                if alias_id in self.prefs:
                                    del self.prefs[alias_id]
                                    aliases_removed += 1
                        
                        if aliases_removed > 0:
                            print(f"✓ Убрано {aliases_removed} дублей алиасов "
                                  f"(осталось {len(self.prefs)} записей)")
                    # Старый формат: person_prefs.json
                    else:
                        self.prefs = data
                        self.aliases = {}
                        print(f"Загружен старый формат")
                    
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
        """Сохранить настройки сотрудников"""
        try:
            self.prefs_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Определяем формат файла
            if 'person_mapping' in str(self.prefs_file):
                # Новый формат с aliases
                data = {
                    "README": "Конфигурация для маппинга сотрудников",
                    "person_mappings": self.prefs,
                    "aliases": self.aliases
                }
            else:
                # Старый формат
                data = self.prefs
            
            with open(self.prefs_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Ошибка сохранения prefs: {e}")
        return False
    
    def get_persons_list(self) -> List[str]:
        """Получить список сотрудников"""
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
        """Загрузить конфигурацию приложения"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                self.files = config.get('files', [])
                self.use_ai = config.get('use_ai', True)
                self.verbose = config.get('verbose', False)
                
                # Проверяем путь к prefs_file
                prefs_path = config.get('prefs_file', 'path/person_prefs.json')
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
        """Сохранить конфигурацию приложения"""
        try:
            config = {
                'files': self.files,
                'use_ai': self.use_ai,
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


class SettingsInterface(QWidget):
    """Интерфейс настроек"""
    
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("settingsInterface")
        
        # Главный layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)
        
        # Заголовок
        title = StrongBodyLabel("Настройки анализа", self)
        layout.addWidget(title)
        
        # Карточка: Файлы логов
        files_card = CardWidget(self)
        files_layout = QVBoxLayout(files_card)
        files_layout.setSpacing(12)
        
        files_label = StrongBodyLabel("Файлы логов")
        files_layout.addWidget(files_label)
        
        # Кнопки управления файлами
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)
        
        self.add_btn = PrimaryPushButton("Добавить файл", self)
        self.add_btn.clicked.connect(self._add_file)
        
        self.add_folder_btn = PushButton("Добавить папку", self)
        self.add_folder_btn.clicked.connect(self._add_folder)
        
        self.clear_btn = PushButton("Очистить", self)
        self.clear_btn.clicked.connect(self._clear_files)
        
        buttons_layout.addWidget(self.add_btn)
        buttons_layout.addWidget(self.add_folder_btn)
        buttons_layout.addWidget(self.clear_btn)
        buttons_layout.addStretch()
        
        files_layout.addLayout(buttons_layout)
        
        # Список файлов
        self.files_list = ListWidget(self)
        self.files_list.setMaximumHeight(150)
        files_layout.addWidget(self.files_list)
        
        layout.addWidget(files_card)
        
        # Карточка: Пути
        paths_card = CardWidget(self)
        paths_layout = QVBoxLayout(paths_card)
        paths_layout.setSpacing(12)
        
        paths_label = StrongBodyLabel("Пути к файлам")
        paths_layout.addWidget(paths_label)
        
        # Person prefs
        prefs_layout = QHBoxLayout()
        prefs_layout.setSpacing(8)
        
        self.prefs_edit = LineEdit(self)
        self.prefs_edit.setPlaceholderText("path/person_prefs.json")
        self.prefs_edit.setText("path/person_prefs.json")
        
        self.prefs_btn = PushButton("Обзор", self)
        self.prefs_btn.clicked.connect(self._select_prefs_file)
        
        prefs_layout.addWidget(BodyLabel("Настройки сотрудников:"))
        prefs_layout.addWidget(self.prefs_edit)
        prefs_layout.addWidget(self.prefs_btn)
        
        paths_layout.addLayout(prefs_layout)
        
        # Export directory
        export_layout = QHBoxLayout()
        export_layout.setSpacing(8)
        
        self.export_edit = LineEdit(self)
        self.export_edit.setPlaceholderText("reports/")
        self.export_edit.setText("reports/")
        
        self.export_btn = PushButton("Обзор", self)
        self.export_btn.clicked.connect(self._select_export_dir)
        
        export_layout.addWidget(BodyLabel("Папка для отчётов:"))
        export_layout.addWidget(self.export_edit)
        export_layout.addWidget(self.export_btn)
        
        paths_layout.addLayout(export_layout)
        
        layout.addWidget(paths_card)
        
        # Карточка: Опции
        options_card = CardWidget(self)
        options_layout = QVBoxLayout(options_card)
        options_layout.setSpacing(12)
        
        options_label = StrongBodyLabel("Опции анализа")
        options_layout.addWidget(options_label)
        
        self.ai_check = CheckBox("Использовать AI анализ (GigaChat)", self)
        self.ai_check.setChecked(True)
        options_layout.addWidget(self.ai_check)
        
        self.verbose_check = CheckBox(
            "Подробный вывод в консоль", self
        )
        self.verbose_check.setChecked(False)
        options_layout.addWidget(self.verbose_check)
        
        layout.addWidget(options_card)
        
        # Кнопки действий
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(8)
        
        self.save_config_btn = PushButton("Сохранить конфигурацию", self)
        self.save_config_btn.setMinimumHeight(36)
        
        self.apply_btn = PrimaryPushButton("Применить настройки", self)
        self.apply_btn.setMinimumHeight(36)
        
        actions_layout.addWidget(self.save_config_btn)
        actions_layout.addWidget(self.apply_btn)
        actions_layout.addStretch()
        
        layout.addLayout(actions_layout)
        
        layout.addStretch()
    
    def _select_prefs_file(self):
        """Выбрать файл person_prefs.json"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл настроек сотрудников",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            self.prefs_edit.setText(file_path)
    
    def _select_export_dir(self):
        """Выбрать директорию для экспорта"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку для отчётов"
        )
        if dir_path:
            self.export_edit.setText(dir_path)
    
    def _add_folder(self):
        """Добавить все файлы из папки"""
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку с файлами логов"
        )
        if folder_path:
            folder = Path(folder_path)
            files_added = 0
            for ext in ['*.csv', '*.ndjson']:
                for file_path in folder.rglob(ext):
                    self.files_list.addItem(str(file_path))
                    files_added += 1
            
            if files_added == 0:
                InfoBar.warning(
                    title="Файлы не найдены",
                    content="В выбранной папке нет файлов .csv или .ndjson",
                    parent=self.window(),
                    position=InfoBarPosition.TOP
                )
            else:
                InfoBar.success(
                    title="Файлы добавлены",
                    content=f"Добавлено файлов: {files_added}",
                    parent=self.window(),
                    position=InfoBarPosition.TOP
                )
    
    def _add_file(self):
        """Добавить файл"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл",
            "",
            "Log Files (*.csv *.ndjson);;All Files (*)"
        )
        if file_path:
            self.files_list.addItem(file_path)
    
    def _clear_files(self):
        """Очистить список файлов"""
        self.files_list.clear()


class PersonsInterface(QWidget):
    """Интерфейс управления сотрудниками"""
    
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("personsInterface")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)
        
        title = StrongBodyLabel("Управление сотрудниками", self)
        layout.addWidget(title)
        
        # Карточка управления
        card = CardWidget(self)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        
        info_label = BodyLabel("Список сотрудников с настройками и алиасами")
        card_layout.addWidget(info_label)
        
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)
        
        self.refresh_btn = PrimaryPushButton("Обновить", self)
        self.add_person_btn = PushButton("Добавить", self)
        self.edit_person_btn = PushButton("Редактировать", self)
        self.delete_person_btn = PushButton("Удалить", self)
        
        buttons_layout.addWidget(self.refresh_btn)
        buttons_layout.addWidget(self.add_person_btn)
        buttons_layout.addWidget(self.edit_person_btn)
        buttons_layout.addWidget(self.delete_person_btn)
        buttons_layout.addStretch()
        
        card_layout.addLayout(buttons_layout)
        
        # Таблица сотрудников
        from PySide6.QtWidgets import QTableWidget
        self.persons_table = QTableWidget(self)
        self.persons_table.setColumnCount(5)
        self.persons_table.setHorizontalHeaderLabels([
            "ID", "Имя", "Время начала", "Рабочие дни", "Алиасы"
        ])
        
        # Настройки таблицы
        header = self.persons_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        # Разрешаем выделение отдельных ячеек для копирования
        self.persons_table.setSelectionMode(
            QTableWidget.SelectionMode.ExtendedSelection
        )
        self.persons_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.persons_table.setSortingEnabled(True)
        
        card_layout.addWidget(self.persons_table)
        
        layout.addWidget(card)
    
    def refresh_persons_table(self, prefs: Dict, aliases: Dict):
        """Обновить таблицу сотрудников"""
        self.persons_table.setSortingEnabled(False)
        self.persons_table.setRowCount(0)
        
        # Находим алиасы для каждого ID
        reverse_aliases = {}
        aliased_ids = set()  # ID которые являются алиасами других
        
        for main_id, alias_list in aliases.items():
            if main_id != 'NOTE' and isinstance(alias_list, list):
                reverse_aliases[main_id] = alias_list
                # Добавляем все алиасы в набор
                for alias_id in alias_list:
                    aliased_ids.add(str(alias_id))
        
        row = 0
        for person_id, person_data in prefs.items():
            if not isinstance(person_data, dict):
                continue
            
            # Пропускаем ID которые являются алиасами
            if str(person_id) in aliased_ids:
                continue
            
            self.persons_table.insertRow(row)
            
            # ID
            self.persons_table.setItem(
                row, 0, QTableWidgetItem(person_id)
            )
            
            # Имя
            display_name = person_data.get('display_name', person_id)
            self.persons_table.setItem(
                row, 1, QTableWidgetItem(display_name)
            )
            
            # Время начала
            start_time = person_data.get('start_time', '-')
            self.persons_table.setItem(
                row, 2, QTableWidgetItem(start_time)
            )
            
            # Рабочие дни
            workdays = person_data.get('workdays', [])
            workdays_str = ', '.join(workdays) if workdays else '-'
            self.persons_table.setItem(
                row, 3, QTableWidgetItem(workdays_str)
            )
            
            # Алиасы
            person_aliases = reverse_aliases.get(person_id, [])
            aliases_str = ', '.join(person_aliases) if person_aliases else '-'
            self.persons_table.setItem(
                row, 4, QTableWidgetItem(aliases_str)
            )
            
            row += 1
        
        self.persons_table.setSortingEnabled(True)
    
    def get_selected_person_id(self) -> Optional[str]:
        """Получить ID выбранного сотрудника"""
        selected_rows = self.persons_table.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            return self.persons_table.item(row, 0).text()
        
        # Если строка не выбрана, проверяем выбранные ячейки
        selected = self.persons_table.selectedItems()
        if selected and len(selected) > 0:
            row = selected[0].row()
            return self.persons_table.item(row, 0).text()
        return None


class LogDownloadWorker(QThread):
    """Worker для загрузки логов с устройства"""
    progress = Signal(str)  # Сообщение о прогрессе
    finished = Signal(str)  # Путь к файлу
    error = Signal(str)     # Сообщение об ошибке
    
    def __init__(self, host, user, password, start_date, end_date,
                 output_file, major=5, minor=75, pic_enable=False):
        super().__init__()
        self.host = host
        self.user = user
        self.password = password
        self.start_date = start_date
        self.end_date = end_date
        self.output_file = output_file
        self.major = major
        self.minor = minor
        self.pic_enable = pic_enable
    
    def run(self):
        """Выполнение загрузки"""
        try:
            import requests
            from requests.auth import HTTPDigestAuth
            
            self.progress.emit("🔌 Подключение к устройству...")
            
            base_url = f"http://{self.host}"
            auth = HTTPDigestAuth(self.user, self.password)
            session = requests.Session()
            
            # Подготовка условий запроса
            cond = {
                "searchID": "1",
                "searchResultPosition": 0,
                "maxResults": 30,
                "major": self.major,
                "minor": self.minor,
                "startTime": self.start_date,
                "endTime": self.end_date,
            }
            
            if self.pic_enable:
                cond["picEnable"] = True
            
            url = f"{base_url}/ISAPI/AccessControl/AcsEvent?format=json"
            timeout = (5, 30)
            
            all_events = []
            page = 1
            
            while True:
                self.progress.emit(f"📥 Страница {page}...")
                
                try:
                    resp = session.post(url, auth=auth, json={"AcsEventCond": cond}, timeout=timeout)
                    
                    if resp.status_code == 401:
                        raise RuntimeError("Ошибка авторизации (401)")
                    if resp.status_code >= 400:
                        raise RuntimeError(f"HTTP {resp.status_code}")
                    
                    # Парсим ответ
                    payload = resp.json()
                    
                    # Извлекаем события
                    acs = payload.get("AcsEvent", {})
                    info_list = acs.get("InfoList", [])
                    
                    if not info_list:
                        break
                    
                    all_events.extend(info_list)
                    self.progress.emit(f"✓ Получено событий: {len(all_events)}")
                    
                    # Проверяем, есть ли еще страницы
                    total = acs.get("totalMatches", 0)
                    if len(all_events) >= total or len(info_list) < 30:
                        break
                    
                    # Следующая страница
                    cond["searchResultPosition"] = len(all_events)
                    page += 1
                    
                except Exception as e:
                    self.error.emit(f"Ошибка запроса: {str(e)}")
                    return
            
            # Сохраняем в NDJSON
            self.progress.emit(f"💾 Сохранение в {self.output_file.name}...")
            
            with open(self.output_file, 'w', encoding='utf-8') as f:
                for event in all_events:
                    f.write(json.dumps(event, ensure_ascii=False) + '\n')
            
            self.progress.emit(f"✅ Готово! Сохранено {len(all_events)} событий")
            self.finished.emit(str(self.output_file))
            
        except Exception as e:
            self.error.emit(f"❌ Ошибка: {str(e)}")


class LogsInterface(QWidget):
    """Интерфейс управления логами"""
    
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("logsInterface")
        self.download_worker = None
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)
        
        title = StrongBodyLabel("Управление логами", self)
        layout.addWidget(title)
        
        # Карточка: Получение логов с устройства
        fetch_card = CardWidget(self)
        fetch_layout = QVBoxLayout(fetch_card)
        fetch_layout.setSpacing(12)
        
        fetch_label = StrongBodyLabel("Получение логов с устройства")
        fetch_layout.addWidget(fetch_label)
        
        info_label = BodyLabel(
            "Подключение к устройству HIKVISION для получения событий"
        )
        fetch_layout.addWidget(info_label)
        
        # Настройки устройства
        device_form = QHBoxLayout()
        device_form.setSpacing(8)
        
        self.host_edit = LineEdit(self)
        self.host_edit.setPlaceholderText("192.168.1.101")
        self.host_edit.setText("192.168.1.101")
        
        self.user_edit = LineEdit(self)
        self.user_edit.setPlaceholderText("admin")
        self.user_edit.setText("admin")
        
        self.password_edit = LineEdit(self)
        self.password_edit.setPlaceholderText("пароль")
        self.password_edit.setEchoMode(LineEdit.EchoMode.Password)
        
        device_form.addWidget(BodyLabel("IP:"))
        device_form.addWidget(self.host_edit)
        device_form.addWidget(BodyLabel("Логин:"))
        device_form.addWidget(self.user_edit)
        device_form.addWidget(BodyLabel("Пароль:"))
        device_form.addWidget(self.password_edit)
        
        fetch_layout.addLayout(device_form)
        
        # Диапазон дат
        dates_form = QHBoxLayout()
        dates_form.setSpacing(8)
        
        from datetime import datetime, timedelta
        from qfluentwidgets import DatePicker
        from PySide6.QtCore import QDate
        
        today = datetime.now()
        week_ago = today - timedelta(days=7)
        
        # DatePicker - легкий виджет с диалогом
        self.start_date_picker = DatePicker(self)
        self.start_date_picker.setDate(
            QDate(week_ago.year, week_ago.month, week_ago.day)
        )
        
        self.end_date_picker = DatePicker(self)
        self.end_date_picker.setDate(
            QDate(today.year, today.month, today.day)
        )
        
        dates_form.addWidget(BodyLabel("От:"))
        dates_form.addWidget(self.start_date_picker)
        dates_form.addWidget(BodyLabel("До:"))
        dates_form.addWidget(self.end_date_picker)
        
        fetch_layout.addLayout(dates_form)
        
        # Дополнительные параметры
        params_form = QHBoxLayout()
        params_form.setSpacing(8)
        
        self.major_edit = LineEdit(self)
        self.major_edit.setText("5")
        self.major_edit.setFixedWidth(60)
        
        self.minor_edit = LineEdit(self)
        self.minor_edit.setText("75")
        self.minor_edit.setFixedWidth(60)
        
        self.pic_check = CheckBox("Загружать фото", self)
        
        params_form.addWidget(BodyLabel("Major:"))
        params_form.addWidget(self.major_edit)
        params_form.addWidget(BodyLabel("Minor:"))
        params_form.addWidget(self.minor_edit)
        params_form.addWidget(self.pic_check)
        params_form.addStretch()
        
        fetch_layout.addLayout(params_form)
        
        # Область прогресса
        from PySide6.QtWidgets import QTextEdit
        self.progress_text = QTextEdit(self)
        self.progress_text.setReadOnly(True)
        self.progress_text.setMaximumHeight(100)
        self.progress_text.setPlaceholderText("Здесь будет отображаться прогресс...")
        fetch_layout.addWidget(self.progress_text)
        
        # Кнопка получения логов
        self.fetch_btn = PrimaryPushButton("Получить логи", self)
        self.fetch_btn.setMinimumHeight(36)
        fetch_layout.addWidget(self.fetch_btn)
        
        layout.addWidget(fetch_card)
        
        # Карточка: Импорт новых сотрудников
        import_card = CardWidget(self)
        import_layout = QVBoxLayout(import_card)
        import_layout.setSpacing(12)
        
        import_label = StrongBodyLabel("Импорт новых сотрудников из логов")
        import_layout.addWidget(import_label)
        
        import_info = BodyLabel(
            "Найти новых сотрудников в NDJSON файлах и добавить в конфигурацию"
        )
        import_layout.addWidget(import_info)
        
        # Выбор файла
        file_layout = QHBoxLayout()
        file_layout.setSpacing(8)
        
        self.ndjson_edit = LineEdit(self)
        self.ndjson_edit.setPlaceholderText("logs/events.ndjson")
        
        self.browse_ndjson_btn = PushButton("Обзор", self)
        
        file_layout.addWidget(BodyLabel("NDJSON файл:"))
        file_layout.addWidget(self.ndjson_edit)
        file_layout.addWidget(self.browse_ndjson_btn)
        
        import_layout.addLayout(file_layout)
        
        # Кнопка импорта
        self.import_btn = PrimaryPushButton("Импортировать новых", self)
        self.import_btn.setMinimumHeight(36)
        import_layout.addWidget(self.import_btn)
        
        layout.addWidget(import_card)
        
        layout.addStretch()
        
        # Подключаем обработчики
        self.browse_ndjson_btn.clicked.connect(self._on_browse_ndjson)
        self.fetch_btn.clicked.connect(self._on_fetch_logs)
        self.import_btn.clicked.connect(self._on_import_employees)
    
    def _on_browse_ndjson(self):
        """Выбор NDJSON файла для импорта"""
        from PySide6.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите NDJSON файл",
            str(Path.cwd() / "logs"),
            "NDJSON файлы (*.ndjson);;Все файлы (*.*)"
        )
        
        if file_path:
            self.ndjson_edit.setText(file_path)
    
    def _on_fetch_logs(self):
        """Получить логи с устройства"""
        # Проверка, не запущен ли уже процесс
        if self.download_worker and self.download_worker.isRunning():
            InfoBar.warning(
                title="Внимание",
                content="Загрузка уже выполняется",
                parent=self
            )
            return
        
        host = self.host_edit.text().strip()
        user = self.user_edit.text().strip()
        password = self.password_edit.text().strip()
        
        # Получаем даты из DatePicker (getDate возвращает QDate)
        start_qdate = self.start_date_picker.getDate()
        end_qdate = self.end_date_picker.getDate()
        
        # Форматируем в ISO формат
        start_date = start_qdate.toString("yyyy-MM-dd") + "T00:00:00"
        end_date = end_qdate.toString("yyyy-MM-dd") + "T23:59:59"
        
        if not all([host, user, password]):
            InfoBar.warning(
                title="Ошибка",
                content="Заполните все поля подключения",
                parent=self
            )
            return
        
        # Получаем параметры
        try:
            major = int(self.major_edit.text())
            minor = int(self.minor_edit.text())
        except ValueError:
            InfoBar.warning(
                title="Ошибка",
                content="Major и Minor должны быть числами",
                parent=self
            )
            return
        
        pic_enable = self.pic_check.isChecked()
        
        # Создаем имя файла с текущей датой
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = Path.cwd() / "logs" / f"events_{timestamp}.ndjson"
        output_file.parent.mkdir(exist_ok=True)
        
        # Очищаем прогресс
        self.progress_text.clear()
        self.progress_text.append(f"🚀 Начинаем загрузку с {host}...")
        
        # Отключаем кнопку
        self.fetch_btn.setEnabled(False)
        self.fetch_btn.setText("Загрузка...")
        
        # Создаем и запускаем worker
        self.download_worker = LogDownloadWorker(
            host, user, password, start_date, end_date,
            output_file, major, minor, pic_enable
        )
        
        # Подключаем сигналы
        self.download_worker.progress.connect(self._on_download_progress)
        self.download_worker.finished.connect(self._on_download_finished)
        self.download_worker.error.connect(self._on_download_error)
        
        # Запускаем
        self.download_worker.start()
    
    def _on_download_progress(self, message):
        """Обновление прогресса"""
        self.progress_text.append(message)
        # Прокручиваем вниз
        cursor = self.progress_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.progress_text.setTextCursor(cursor)
    
    def _on_download_finished(self, file_path):
        """Загрузка завершена"""
        self.fetch_btn.setEnabled(True)
        self.fetch_btn.setText("Получить логи")
        
        InfoBar.success(
            title="Успешно",
            content=f"Логи сохранены в:\n{file_path}",
            parent=self
        )
        
        # Добавляем файл в список для импорта
        self.ndjson_edit.setText(file_path)
    
    def _on_download_error(self, error_message):
        """Ошибка загрузки"""
        self.fetch_btn.setEnabled(True)
        self.fetch_btn.setText("Получить логи")
        
        self.progress_text.append(error_message)
        
        InfoBar.error(
            title="Ошибка",
            content=error_message,
            parent=self
        )
    
    def _on_import_employees(self):
        """Импортировать новых сотрудников из NDJSON"""
        ndjson_path = self.ndjson_edit.text().strip()
        
        if not ndjson_path:
            InfoBar.warning(
                title="Ошибка",
                content="Укажите путь к NDJSON файлу",
                parent=self
            )
            return
        
        ndjson_file = Path(ndjson_path)
        if not ndjson_file.exists():
            InfoBar.error(
                title="Ошибка",
                content=f"Файл не найден:\n{ndjson_path}",
                parent=self
            )
            return
        
        # Получаем родительское окно с состоянием
        main_window = self.window()
        if not hasattr(main_window, 'state'):
            InfoBar.error(
                title="Ошибка",
                content="Не удалось получить доступ к настройкам",
                parent=self
            )
            return
        
        # Загружаем ПОЛНЫЙ список существующих ID из файла
        # (включая основные ID и все алиасы)
        existing_ids = set()
        try:
            import json
            prefs_file = Path(main_window.state.prefs_file)
            if prefs_file.exists():
                with open(prefs_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Собираем все ID из person_mappings
                person_mappings = data.get('person_mappings', {})
                existing_ids.update(person_mappings.keys())
                
                # Добавляем все алиасы
                aliases_data = data.get('aliases', {})
                for main_id, alias_list in aliases_data.items():
                    if main_id != 'NOTE' and isinstance(alias_list, list):
                        existing_ids.update(alias_list)
                
                print(f"✓ Загружено {len(existing_ids)} ID "
                      f"({len(person_mappings)} основных + алиасы)")
                print(f"  Файл: {prefs_file}")
            else:
                print(f"⚠️ Файл не найден: {prefs_file}")
        except Exception as e:
            print(f"❌ Ошибка чтения файла сотрудников: {e}")
            InfoBar.error(
                title="Ошибка",
                content=f"Не удалось прочитать файл сотрудников:\n{e}",
                parent=self
            )
            return
        
        # Сканируем NDJSON на новых сотрудников
        new_employees = {}
        try:
            import json
            with open(ndjson_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        event = json.loads(line)
                        emp_id = event.get('employeeNoString')
                        emp_name = event.get('name', '')
                        
                        if emp_id and emp_id not in existing_ids and emp_id not in new_employees:
                            new_employees[emp_id] = emp_name or emp_id
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            InfoBar.error(
                title="Ошибка чтения файла",
                content=str(e),
                parent=self
            )
            return
        
        if not new_employees:
            InfoBar.success(
                title="Импорт завершен",
                content="Новых сотрудников не найдено",
                parent=self
            )
            return
        
        # Показываем диалог с новыми сотрудниками
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Новые сотрудники")
        dialog.setMinimumWidth(500)
        dialog.setMinimumHeight(400)
        
        layout = QVBoxLayout(dialog)
        
        # Показываем информацию о файле сотрудников
        prefs_info = BodyLabel(
            f"Файл сотрудников: {main_window.state.prefs_file}"
        )
        layout.addWidget(prefs_info)
        
        info = BodyLabel(
            f"Найдено новых сотрудников: {len(new_employees)}"
        )
        layout.addWidget(info)
        
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        employees_text = "\n".join([f"{emp_id}: {name}" for emp_id, name in new_employees.items()])
        text_edit.setPlainText(employees_text)
        layout.addWidget(text_edit)
        
        btn_layout = QHBoxLayout()
        add_btn = PrimaryPushButton("Добавить всех")
        cancel_btn = PushButton("Отмена")
        
        def add_employees():
            # Добавляем новых сотрудников в конфигурацию
            for emp_id, emp_name in new_employees.items():
                # main_window.state.prefs уже содержит person_mappings
                main_window.state.prefs[emp_id] = {
                    "display_name": emp_name,
                    "original_names": [emp_name],
                    "workdays": [
                        "Monday", "Tuesday", "Wednesday", 
                        "Thursday", "Friday"
                    ],
                    "start_time": "09:00",
                    "end_time": "18:00",
                    "work_hours": 9
                }
            
            # Сохраняем конфигурацию
            main_window.state.save_prefs()
            
            # Обновляем таблицу сотрудников
            if hasattr(main_window, 'personsInterface'):
                main_window.personsInterface.refresh_persons_table(
                    main_window.state.prefs, 
                    main_window.state.aliases
                )
            
            InfoBar.success(
                title="Успешно",
                content=f"Добавлено сотрудников: {len(new_employees)}",
                parent=self
            )
            dialog.accept()
        
        add_btn.clicked.connect(add_employees)
        cancel_btn.clicked.connect(dialog.reject)
        
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        dialog.exec()
    
    def set_default_ndjson_from_settings(self, files):
        """Установить путь к NDJSON файлу из настроек"""
        if not files:
            return
        
        # Берем первый NDJSON файл из списка
        for file_path in files:
            # Нормализуем путь (Path автоматически обработает слеши)
            if isinstance(file_path, str):
                normalized_path = Path(file_path)
            else:
                normalized_path = file_path
            
            file_str = str(normalized_path)
            
            # Проверяем расширение и существование файла
            if file_str.lower().endswith('.ndjson'):
                self.ndjson_edit.setText(file_str)
                print(f"✓ NDJSON файл установлен: {file_str}")
                return
        
        # Если NDJSON файлов нет, берем первый файл
        if files:
            first_file = str(files[0])
            self.ndjson_edit.setText(first_file)
            print(f"✓ Установлен первый файл: {first_file}")


class ExportInterface(QWidget):
    """Интерфейс экспорта"""
    
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("exportInterface")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)
        
        title = StrongBodyLabel("Экспорт данных", self)
        layout.addWidget(title)
        
        # Карточка экспорта
        card = CardWidget(self)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        
        info_label = BodyLabel("Экспорт результатов анализа в различные форматы")
        card_layout.addWidget(info_label)
        
        # Опции экспорта
        self.excel_check = CheckBox("Экспорт в Excel (.xlsx)", self)
        self.excel_check.setChecked(True)
        card_layout.addWidget(self.excel_check)
        
        self.csv_check = CheckBox("Экспорт в CSV", self)
        card_layout.addWidget(self.csv_check)
        
        # Кнопка экспорта
        self.export_btn = PrimaryPushButton("Экспортировать", self)
        self.export_btn.setMinimumHeight(36)
        card_layout.addWidget(self.export_btn)
        
        layout.addWidget(card)
        layout.addStretch()


class AnalysisInterface(QWidget):
    """Интерфейс анализа"""
    
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("analysisInterface")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)
        
        title = StrongBodyLabel("Анализ логов", self)
        layout.addWidget(title)
        
        # Карточка статуса
        status_card = CardWidget(self)
        status_layout = QVBoxLayout(status_card)
        status_layout.setSpacing(12)
        
        self.status_label = BodyLabel("Готов к анализу")
        status_layout.addWidget(self.status_label)
        
        # Прогресс бар
        self.progress_bar = IndeterminateProgressBar(self)
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.progress_bar)
        
        # Кнопка запуска
        self.run_btn = PrimaryPushButton("Запустить анализ", self)
        self.run_btn.setMinimumHeight(36)
        status_layout.addWidget(self.run_btn)
        
        layout.addWidget(status_card)
        
        # Карточка результатов
        results_card = CardWidget(self)
        results_layout = QVBoxLayout(results_card)
        results_layout.setSpacing(12)
        
        results_label = StrongBodyLabel("Результаты анализа")
        results_layout.addWidget(results_label)
        
        self.results_list = ListWidget(self)
        results_layout.addWidget(self.results_list)
        
        layout.addWidget(results_card)
        layout.addStretch()
    
    def set_analyzing(self, analyzing: bool):
        """Установить состояние анализа"""
        self.run_btn.setEnabled(not analyzing)
        self.progress_bar.setVisible(analyzing)
        if analyzing:
            self.progress_bar.start()
        else:
            self.progress_bar.stop()


class AboutInterface(QWidget):
    """Интерфейс О программе"""
    
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("aboutInterface")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)
        
        title = StrongBodyLabel("О программе", self)
        layout.addWidget(title)
        
        # Карточка с информацией
        card = CardWidget(self)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(16)
        
        app_name = StrongBodyLabel("LogStorm")
        card_layout.addWidget(app_name)
        
        version_label = BodyLabel("Версия 2.7")
        card_layout.addWidget(version_label)
        
        desc_label = BodyLabel(
            "Система анализа логов посещений с использованием AI\n\n"
            "Функции:\n"
            "• Анализ логов посещений сотрудников\n"
            "• Интеллектуальное определение причин отсутствия\n"
            "• Управление графиками работы\n"
            "• Экспорт отчётов в Excel"
        )
        card_layout.addWidget(desc_label)
        
        layout.addWidget(card)
        layout.addStretch()


class LogStormWindow(FluentWindow):
    """Главное окно приложения"""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("LogStorm - Анализ логов посещений")
        self.resize(1100, 750)
        
        # Состояние приложения
        self.state = AppState()
        
        # Создаём интерфейсы
        self.settingsInterface = SettingsInterface(self)
        self.personsInterface = PersonsInterface(self)
        self.logsInterface = LogsInterface(self)
        self.analysisInterface = AnalysisInterface(self)
        self.exportInterface = ExportInterface(self)
        self.aboutInterface = AboutInterface(self)
        
        self._init_navigation()
        self._connect_signals()
        self._load_initial_data()
        
        # Применяем тему системы
        self._apply_system_theme()
    
    def _load_initial_data(self):
        """Загрузить начальные данные"""
        # Загружаем конфигурацию
        if self.state.load_config():
            # Обновляем UI
            self.settingsInterface.prefs_edit.setText(
                str(self.state.prefs_file)
            )
            self.settingsInterface.export_edit.setText(
                str(self.state.export_dir)
            )
            self.settingsInterface.ai_check.setChecked(self.state.use_ai)
            self.settingsInterface.verbose_check.setChecked(
                self.state.verbose
            )
            
            # Загружаем файлы в список
            for file_path in self.state.files:
                self.settingsInterface.files_list.addItem(file_path)
        
        # Загружаем настройки сотрудников
        if self.state.load_prefs():
            self.personsInterface.refresh_persons_table(
                self.state.prefs, self.state.aliases
            )
            InfoBar.success(
                title="Загружено",
                content=f"Найдено сотрудников: {len(self.state.prefs)}",
                parent=self,
                position=InfoBarPosition.TOP
            )
        else:
            InfoBar.warning(
                title="Внимание",
                content="Файл person_prefs.json не найден",
                parent=self,
                position=InfoBarPosition.TOP
            )
        
        # Устанавливаем путь к NDJSON из настроек
        self.logsInterface.set_default_ndjson_from_settings(
            self.state.files
        )
    
    def _connect_signals(self):
        """Подключить сигналы"""
        # Настройки
        self.settingsInterface.apply_btn.clicked.connect(
            self._on_apply_settings
        )
        self.settingsInterface.save_config_btn.clicked.connect(
            self._on_save_config
        )
        
        # Сотрудники
        self.personsInterface.refresh_btn.clicked.connect(
            self._on_refresh_persons
        )
        self.personsInterface.add_person_btn.clicked.connect(
            self._on_add_person
        )
        self.personsInterface.edit_person_btn.clicked.connect(
            self._on_edit_person
        )
        self.personsInterface.delete_person_btn.clicked.connect(
            self._on_delete_person
        )
        
        # Анализ
        self.analysisInterface.run_btn.clicked.connect(
            self._on_run_analysis
        )
        
        # Экспорт
        self.exportInterface.export_btn.clicked.connect(
            self._on_export
        )
    
    def _on_refresh_persons(self):
        """Обновить список сотрудников"""
        if self.state.load_prefs():
            self.personsInterface.refresh_persons_table(
                self.state.prefs, self.state.aliases
            )
            InfoBar.success(
                title="Обновлено",
                content=f"Загружено сотрудников: {len(self.state.prefs)}",
                parent=self,
                position=InfoBarPosition.TOP
            )
    
    def _on_add_person(self):
        """Добавить сотрудника"""
        dialog = PersonDialog(parent=self)
        if dialog.exec():
            person_id, person_data = dialog.get_person_data()
            
            if not person_id or not person_data.get('display_name'):
                InfoBar.error(
                    title="Ошибка",
                    content="Заполните обязательные поля: ID и Имя",
                    parent=self,
                    position=InfoBarPosition.TOP
                )
                return
            
            if person_id in self.state.prefs:
                InfoBar.warning(
                    title="Предупреждение",
                    content=f"Сотрудник {person_id} уже существует",
                    parent=self,
                    position=InfoBarPosition.TOP
                )
                return
            
            # Извлекаем алиасы из данных (если есть)
            aliases = person_data.pop('_aliases', [])
            
            # Сохраняем основные данные
            self.state.prefs[person_id] = person_data
            
            # Сохраняем алиасы и убеждаемся что алиасы НЕ имеют своих записей
            if aliases:
                self.state.aliases[person_id] = aliases
                # Удаляем записи для алиасов (они должны быть только под основным ID)
                for alias_id in aliases:
                    if alias_id in self.state.prefs:
                        del self.state.prefs[alias_id]
            elif person_id in self.state.aliases:
                del self.state.aliases[person_id]
            
            if self.state.save_prefs():
                self.personsInterface.refresh_persons_table(
                    self.state.prefs, self.state.aliases
                )
                InfoBar.success(
                    title="Успешно",
                    content=f"Сотрудник {person_data['display_name']} добавлен",
                    parent=self,
                    position=InfoBarPosition.TOP
                )
    
    def _on_edit_person(self):
        """Редактировать сотрудника"""
        person_id = self.personsInterface.get_selected_person_id()
        if not person_id:
            InfoBar.warning(
                title="Выберите сотрудника",
                content="Выберите сотрудника из таблицы для редактирования",
                parent=self,
                position=InfoBarPosition.TOP
            )
            return
        
        # Подготавливаем данные для редактирования (включая алиасы)
        person_data = self.state.prefs.get(person_id, {}).copy()
        person_data['_aliases'] = self.state.aliases.get(person_id, [])
        
        dialog = PersonDialog(
            person_id=person_id,
            person_data=person_data,
            parent=self
        )
        
        if dialog.exec():
            _, updated_data = dialog.get_person_data()
            
            # Извлекаем алиасы из обновлённых данных
            aliases = updated_data.pop('_aliases', [])
            
            # Сохраняем основные данные
            self.state.prefs[person_id] = updated_data
            
            # Сохраняем алиасы и убеждаемся что алиасы НЕ имеют своих записей
            if aliases:
                self.state.aliases[person_id] = aliases
                # Удаляем записи для алиасов (они должны быть только под основным ID)
                for alias_id in aliases:
                    if alias_id in self.state.prefs:
                        del self.state.prefs[alias_id]
            elif person_id in self.state.aliases:
                del self.state.aliases[person_id]
            
            if self.state.save_prefs():
                self.personsInterface.refresh_persons_table(
                    self.state.prefs, self.state.aliases
                )
                InfoBar.success(
                    title="Успешно",
                    content="Данные сотрудника обновлены",
                    parent=self,
                    position=InfoBarPosition.TOP
                )
    
    def _on_delete_person(self):
        """Удалить сотрудника"""
        person_id = self.personsInterface.get_selected_person_id()
        if not person_id:
            InfoBar.warning(
                title="Выберите сотрудника",
                content="Выберите сотрудника из таблицы для удаления",
                parent=self,
                position=InfoBarPosition.TOP
            )
            return
        
        person_name = self.state.prefs.get(person_id, {}).get(
            'display_name', person_id
        )
        
        # Подтверждение удаления
        w = MessageBox(
            f"Удалить {person_name}?",
            f"Вы уверены что хотите удалить сотрудника {person_name}?",
            self
        )
        
        if w.exec():
            # Удаляем основные данные
            del self.state.prefs[person_id]
            
            # Удаляем алиасы (если есть)
            if person_id in self.state.aliases:
                del self.state.aliases[person_id]
            
            if self.state.save_prefs():
                self.personsInterface.refresh_persons_table(
                    self.state.prefs, self.state.aliases
                )
                InfoBar.success(
                    title="Успешно",
                    content=f"Сотрудник {person_name} удалён",
                    parent=self,
                    position=InfoBarPosition.TOP
                )
    
    def _on_save_config(self):
        """Сохранить конфигурацию в файл"""
        # Применяем настройки сначала
        self._on_apply_settings()
        
        # Сохраняем в файл
        if self.state.save_config():
            InfoBar.success(
                title="Успешно",
                content="Конфигурация сохранена в config.json",
                parent=self,
                position=InfoBarPosition.TOP
            )
        else:
            InfoBar.error(
                title="Ошибка",
                content="Не удалось сохранить конфигурацию",
                parent=self,
                position=InfoBarPosition.TOP
            )
    
    def _on_apply_settings(self):
        """Применить настройки"""
        # Сохраняем файлы
        self.state.files = [
            self.settingsInterface.files_list.item(i).text()
            for i in range(self.settingsInterface.files_list.count())
        ]
        
        # Сохраняем опции
        self.state.use_ai = self.settingsInterface.ai_check.isChecked()
        self.state.verbose = self.settingsInterface.verbose_check.isChecked()
        
        # Сохраняем пути
        self.state.prefs_file = Path(
            self.settingsInterface.prefs_edit.text()
        )
        self.state.export_dir = Path(
            self.settingsInterface.export_edit.text()
        )
        
        # Перезагружаем prefs если путь изменился
        if self.state.load_prefs():
            self.personsInterface.refresh_persons_table(
                self.state.prefs, self.state.aliases
            )
        
        if self.state.files:
            InfoBar.success(
                title="Успешно",
                content=f"Настройки применены. Файлов: {len(self.state.files)}",
                parent=self,
                position=InfoBarPosition.TOP
            )
        else:
            InfoBar.warning(
                title="Предупреждение",
                content="Не выбрано ни одного файла",
                parent=self,
                position=InfoBarPosition.TOP
            )
    
    def _on_run_analysis(self):
        """Запустить анализ"""
        if not self.state.files:
            InfoBar.error(
                title="Ошибка",
                content="Сначала добавьте файлы в настройках",
                parent=self,
                position=InfoBarPosition.TOP
            )
            return
        
        # Создаём рабочий поток
        self.analysis_worker = AnalysisWorker(
            self.state.files,
            self.state.prefs,
            self.state.use_ai,
            str(self.state.prefs_file)
        )
        
        # Подключаем сигналы
        self.analysis_worker.progress.connect(self._on_analysis_progress)
        self.analysis_worker.finished.connect(self._on_analysis_finished)
        self.analysis_worker.error.connect(self._on_analysis_error)
        
        # Запускаем
        self.analysisInterface.set_analyzing(True)
        self.analysisInterface.results_list.clear()
        self.analysis_worker.start()
    
    def _on_analysis_progress(self, message: str):
        """Обновить прогресс анализа"""
        self.analysisInterface.status_label.setText(message)
    
    def _on_analysis_finished(self, results):
        """Анализ завершён"""
        self.state.results = results
        self.analysisInterface.set_analyzing(False)
        
        # Показываем результаты
        self.analysisInterface.status_label.setText(
            f"Анализ завершён! Обработано записей: {len(results)}"
        )
        
        # Добавляем краткую статистику
        self.analysisInterface.results_list.addItem(
            f"✓ Всего записей: {len(results)}"
        )
        self.analysisInterface.results_list.addItem(
            f"✓ Файлов обработано: {len(self.state.files)}"
        )
        
        # Статистика по проблемам
        records_with_tech = sum(1 for r in results if r.has_technical_issues)
        records_with_employee = sum(1 for r in results if r.has_employee_issues)
        late_records = sum(1 for r in results if r.is_late)
        early_leave_records = sum(1 for r in results if r.is_early_leave)
        overtime_records = sum(1 for r in results if r.is_overtime)
        underwork_records = sum(1 for r in results if r.is_underwork)
        
        self.analysisInterface.results_list.addItem("")
        self.analysisInterface.results_list.addItem("📊 Статистика:")
        self.analysisInterface.results_list.addItem(
            f"  • Технические сбои: {records_with_tech}"
        )
        self.analysisInterface.results_list.addItem(
            f"  • Проблемы сотрудников: {records_with_employee}"
        )
        self.analysisInterface.results_list.addItem(
            f"  • Опоздания: {late_records}"
        )
        self.analysisInterface.results_list.addItem(
            f"  • Ранние уходы: {early_leave_records}"
        )
        self.analysisInterface.results_list.addItem(
            f"  • Переработки: {overtime_records}"
        )
        self.analysisInterface.results_list.addItem(
            f"  • Недоработки: {underwork_records}"
        )
        
        InfoBar.success(
            title="Успешно",
            content="Анализ завершён",
            parent=self,
            position=InfoBarPosition.TOP
        )
    
    def _on_analysis_error(self, error_msg: str):
        """Ошибка анализа"""
        self.analysisInterface.set_analyzing(False)
        self.analysisInterface.status_label.setText("Ошибка анализа")
        InfoBar.error(
            title="Ошибка",
            content=f"Ошибка при анализе: {error_msg}",
            parent=self,
            position=InfoBarPosition.TOP
        )
    
    def _on_export(self):
        """Экспорт результатов"""
        if not self.state.results:
            InfoBar.error(
                title="Ошибка",
                content="Сначала выполните анализ",
                parent=self,
                position=InfoBarPosition.TOP
            )
            return
        
        try:
            # Создаём директорию для экспорта если её нет
            self.state.export_dir.mkdir(parents=True, exist_ok=True)
            
            # Формируем имя файла по умолчанию
            from datetime import datetime
            default_name = f"attendance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            default_path = str(self.state.export_dir / default_name)
            
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Сохранить отчёт",
                default_path,
                "Excel Files (*.xlsx);;CSV Files (*.csv)"
            )
            
            if file_path:
                # ExcelReporter принимает records в конструкторе
                reporter = ExcelReporter(self.state.results)
                reporter.generate_report(file_path)
                
                InfoBar.success(
                    title="Успешно",
                    content=f"Отчёт сохранён: {file_path}",
                    parent=self,
                    position=InfoBarPosition.TOP
                )
        except PermissionError:
            # Файл открыт в другой программе
            InfoBar.error(
                title="Файл занят",
                content="Закройте файл Excel и попробуйте снова",
                parent=self,
                position=InfoBarPosition.TOP
            )
        except Exception as e:
            import traceback
            error_details = f"{str(e)}\n{traceback.format_exc()}"
            print(f"ОШИБКА ЭКСПОРТА:\n{error_details}")
            InfoBar.error(
                title="Ошибка",
                content=f"Ошибка экспорта: {str(e)}",
                parent=self,
                position=InfoBarPosition.TOP
            )
    
    def _init_navigation(self):
        """Инициализация навигации"""
        
        # Добавляем основные вкладки
        self.addSubInterface(
            self.settingsInterface,
            FluentIcon.SETTING,
            'Настройки',
            NavigationItemPosition.TOP
        )
        
        self.addSubInterface(
            self.personsInterface,
            FluentIcon.PEOPLE,
            'Сотрудники',
            NavigationItemPosition.TOP
        )
        
        self.addSubInterface(
            self.logsInterface,
            FluentIcon.CLOUD_DOWNLOAD,
            'Логи',
            NavigationItemPosition.TOP
        )
        
        self.addSubInterface(
            self.analysisInterface,
            FluentIcon.MARKET,
            'Анализ',
            NavigationItemPosition.TOP
        )
        
        self.addSubInterface(
            self.exportInterface,
            FluentIcon.SHARE,
            'Экспорт',
            NavigationItemPosition.TOP
        )
        
        # О программе внизу
        self.addSubInterface(
            self.aboutInterface,
            FluentIcon.INFO,
            'О программе',
            NavigationItemPosition.BOTTOM
        )
    
    def _apply_system_theme(self):
        """Применить системную тему и цвета из Windows"""
        try:
            import darkdetect
            if darkdetect.isDark():
                setTheme(Theme.DARK)
            else:
                setTheme(Theme.LIGHT)
        except Exception:
            setTheme(Theme.LIGHT)
        
        # Применяем системный акцентный цвет Windows
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\DWM"
            )
            accent_color, _ = winreg.QueryValueEx(key, "AccentColor")
            winreg.CloseKey(key)
            
            # Windows хранит цвет в формате AABBGGRR
            # Извлекаем BGR (игнорируем альфа)
            b = (accent_color >> 16) & 0xFF
            g = (accent_color >> 8) & 0xFF
            r = accent_color & 0xFF
            
            from PySide6.QtGui import QColor
            # Используем слегка приглушенную версию для лучшей читаемости
            color = QColor(r, g, b)
            setThemeColor(color)
        except Exception:
            pass  # Если не удалось получить - используем стандартный


def main():
    """Запуск приложения"""
    # Включаем DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    
    app = QApplication(sys.argv)
    
    window = LogStormWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
