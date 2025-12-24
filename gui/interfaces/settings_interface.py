"""
Settings Interface - интерфейс настроек приложения
"""

from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QButtonGroup
)
from PySide6.QtCore import Signal
from qfluentwidgets import (
    CardWidget, PrimaryPushButton, PushButton, ListWidget, CheckBox,
    StrongBodyLabel, BodyLabel, LineEdit, InfoBar, InfoBarPosition,
    RadioButton
)


class SettingsInterface(QWidget):
    """Интерфейс настроек приложения"""
    
    # Сигнал изменения источника данных
    data_source_changed = Signal(str, str)  # (type, path)
    
    def __init__(self, parent=None):
        """
        Инициализация интерфейса настроек
        
        Args:
            parent: Родительский виджет
        """
        super().__init__(parent=parent)
        self.setObjectName("settingsInterface")
        
        self._initializing = True  # Флаг для предотвращения лишних сигналов
        
        # Главный layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)
        
        # Заголовок
        title = StrongBodyLabel("Настройки анализа", self)
        layout.addWidget(title)
        
        # === Карточка: Источник данных ===
        source_card = CardWidget(self)
        source_layout = QVBoxLayout(source_card)
        source_layout.setSpacing(12)
        
        source_label = StrongBodyLabel("Источник данных")
        source_layout.addWidget(source_label)
        
        info_label = BodyLabel(
            "SQLite рекомендуется для больших объёмов данных "
            "(быстрее и меньше памяти)"
        )
        source_layout.addWidget(info_label)
        
        # Радиокнопки выбора источника
        self.source_group = QButtonGroup(self)
        
        source_buttons_layout = QHBoxLayout()
        source_buttons_layout.setSpacing(16)
        
        self.sqlite_radio = RadioButton("SQLite база данных", self)
        self.files_radio = RadioButton("NDJSON/CSV файлы", self)
        
        self.source_group.addButton(self.sqlite_radio, 0)
        self.source_group.addButton(self.files_radio, 1)
        
        self.sqlite_radio.setChecked(True)  # По умолчанию SQLite
        
        source_buttons_layout.addWidget(self.sqlite_radio)
        source_buttons_layout.addWidget(self.files_radio)
        source_buttons_layout.addStretch()
        
        source_layout.addLayout(source_buttons_layout)
        
        # SQLite путь
        sqlite_layout = QHBoxLayout()
        sqlite_layout.setSpacing(8)
        
        self.sqlite_edit = LineEdit(self)
        self.sqlite_edit.setPlaceholderText(
            "//172.11.1.254/Face_ID/data/events.db"
        )
        
        self.sqlite_btn = PushButton("Обзор", self)
        self.sqlite_btn.clicked.connect(self._select_sqlite_file)
        
        sqlite_layout.addWidget(BodyLabel("БД:"))
        sqlite_layout.addWidget(self.sqlite_edit)
        sqlite_layout.addWidget(self.sqlite_btn)
        
        source_layout.addLayout(sqlite_layout)
        
        layout.addWidget(source_card)
        
        # Карточка: Файлы логов (показывается только для files_radio)
        self.files_card = CardWidget(self)
        files_layout = QVBoxLayout(self.files_card)
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
        
        layout.addWidget(files_label)
        
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
        
        # Подключение сигналов
        self.sqlite_radio.toggled.connect(self._on_source_changed)
        self.files_radio.toggled.connect(self._on_source_changed)
        
        # Инициализация видимости
        self._on_source_changed()
        
        # Завершение инициализации
        self._initializing = False
        
        layout.addStretch()
    
    def _on_source_changed(self):
        """Обработка изменения источника данных"""
        is_sqlite = self.sqlite_radio.isChecked()
        self.files_card.setVisible(not is_sqlite)
        
        # Не emit сигнал во время инициализации
        if self._initializing:
            return
        
        # Испускаем сигнал об изменении
        if is_sqlite:
            self.data_source_changed.emit('sqlite', self.sqlite_edit.text())
        else:
            self.data_source_changed.emit('files', '')
    
    def _select_sqlite_file(self):
        """Выбрать SQLite файл"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите SQLite базу данных",
            "",
            "SQLite Files (*.db *.sqlite *.sqlite3);;All Files (*)"
        )
        
        if file_path:
            self.sqlite_edit.setText(file_path)
            InfoBar.success(
                "База выбрана",
                f"Выбран файл: {Path(file_path).name}",
                parent=self,
                duration=2000,
                position=InfoBarPosition.TOP_RIGHT
            )
            self.data_source_changed.emit('sqlite', file_path)
    
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
