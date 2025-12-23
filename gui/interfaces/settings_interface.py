"""
Settings Interface - интерфейс настроек приложения
"""

from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFileDialog
)
from qfluentwidgets import (
    CardWidget, PrimaryPushButton, PushButton, ListWidget, CheckBox,
    StrongBodyLabel, BodyLabel, LineEdit, InfoBar, InfoBarPosition
)


class SettingsInterface(QWidget):
    """Интерфейс настроек приложения"""
    
    def __init__(self, parent=None):
        """
        Инициализация интерфейса настроек
        
        Args:
            parent: Родительский виджет
        """
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
