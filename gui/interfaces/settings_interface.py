"""
Settings Interface - интерфейс настроек приложения
"""

from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QButtonGroup,
    QGridLayout
)
from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from qfluentwidgets import (
    CardWidget, PrimaryPushButton, PushButton, ListWidget, CheckBox,
    StrongBodyLabel, BodyLabel, LineEdit, InfoBar, InfoBarPosition,
    RadioButton, ColorPickerButton, ScrollArea
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
        
        self._initializing = True
        
        # Главный layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Scroll Area для всего содержимого
        scroll = ScrollArea(self)
        scroll.setWidgetResizable(True)
        
        # Контейнер для содержимого
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)  # Уменьшил отступы
        
        # Заголовок
        title = StrongBodyLabel("Настройки анализа", content)
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
        
        # Карточка: Настройка камер
        cameras_card = CardWidget(self)
        cameras_layout = QVBoxLayout(cameras_card)
        cameras_layout.setSpacing(12)
        
        cameras_label = StrongBodyLabel("Настройка камер")
        cameras_layout.addWidget(cameras_label)
        
        # Описание
        cameras_info = BodyLabel(
            "Выберите камеры для определения прихода и ухода.\n"
            "Если не выбрано ни одной камеры, используются все события."
        )
        cameras_info.setWordWrap(True)
        cameras_layout.addWidget(cameras_info)
        
        # Контейнер для списков камер
        cameras_grid = QHBoxLayout()
        cameras_grid.setSpacing(20)
        
        # Колонка: Камеры прихода
        arrival_container = QVBoxLayout()
        arrival_container.setSpacing(8)
        
        arrival_title = StrongBodyLabel("Камеры прихода (вход)")
        arrival_container.addWidget(arrival_title)
        
        # Создаем словарь для хранения чекбоксов камер прихода
        self.arrival_camera_checks = {}
        self.arrival_cameras_layout = QVBoxLayout()
        self.arrival_cameras_layout.setSpacing(4)
        arrival_container.addLayout(self.arrival_cameras_layout)
        
        cameras_grid.addLayout(arrival_container)
        
        # Колонка: Камеры ухода
        departure_container = QVBoxLayout()
        departure_container.setSpacing(8)
        
        departure_title = StrongBodyLabel("Камеры ухода (выход)")
        departure_container.addWidget(departure_title)
        
        # Создаем словарь для хранения чекбоксов камер ухода
        self.departure_camera_checks = {}
        self.departure_cameras_layout = QVBoxLayout()
        self.departure_cameras_layout.setSpacing(4)
        departure_container.addLayout(self.departure_cameras_layout)
        
        cameras_grid.addLayout(departure_container)
        
        cameras_layout.addLayout(cameras_grid)
        
        # Кнопка обновления списка камер
        refresh_cameras_layout = QHBoxLayout()
        self.refresh_cameras_btn = PushButton("Обновить список камер")
        self.refresh_cameras_btn.setFixedHeight(32)
        self.refresh_cameras_btn.clicked.connect(self._refresh_cameras)
        refresh_cameras_layout.addWidget(self.refresh_cameras_btn)
        refresh_cameras_layout.addStretch()
        cameras_layout.addLayout(refresh_cameras_layout)
        
        layout.addWidget(cameras_card)
        
        # === Карточка: Цветовая схема (КОМПАКТНАЯ) ===
        colors_card = CardWidget(content)
        colors_layout = QVBoxLayout(colors_card)
        colors_layout.setSpacing(8)
        
        # Заголовок с кнопкой сброса
        colors_header = QHBoxLayout()
        colors_title = StrongBodyLabel("Цвета отчетов")
        colors_header.addWidget(colors_title)
        colors_header.addStretch()
        
        self.reset_colors_btn = PushButton("Сброс к дефолту")
        self.reset_colors_btn.setFixedHeight(28)
        self.reset_colors_btn.clicked.connect(self._reset_colors)
        colors_header.addWidget(self.reset_colors_btn)
        colors_layout.addLayout(colors_header)
        
        # Компактная сетка в одну строку
        colors_grid = QGridLayout()
        colors_grid.setSpacing(12)
        colors_grid.setContentsMargins(0, 0, 0, 0)
        
        # Одна строка с 5 цветами
        # Нейтральный
        colors_grid.addWidget(BodyLabel("Норма"), 0, 0)
        self.neutral_picker = ColorPickerButton(
            QColor("#FFFFFF"), "", colors_card
        )
        self.neutral_picker.setFixedSize(60, 28)
        colors_grid.addWidget(self.neutral_picker, 1, 0)
        
        # Недоработка
        colors_grid.addWidget(BodyLabel("Недораб."), 0, 1)
        self.warning_picker = ColorPickerButton(
            QColor("#FFA500"), "", colors_card
        )
        self.warning_picker.setFixedSize(60, 28)
        colors_grid.addWidget(self.warning_picker, 1, 1)
        
        # Техсбой
        colors_grid.addWidget(BodyLabel("Техсбой"), 0, 2)
        self.error_picker = ColorPickerButton(
            QColor("#FF0000"), "", colors_card
        )
        self.error_picker.setFixedSize(60, 28)
        colors_grid.addWidget(self.error_picker, 1, 2)
        
        # Переработка
        colors_grid.addWidget(BodyLabel("Перераб."), 0, 3)
        self.success_picker = ColorPickerButton(
            QColor("#00B050"), "", colors_card
        )
        self.success_picker.setFixedSize(60, 28)
        colors_grid.addWidget(self.success_picker, 1, 3)
        
        # Опоздание/Уход
        colors_grid.addWidget(BodyLabel("Опозд./Уход"), 0, 4)
        self.info_picker = ColorPickerButton(
            QColor("#FFFF00"), "", colors_card
        )
        self.info_picker.setFixedSize(60, 28)
        colors_grid.addWidget(self.info_picker, 1, 4)
        
        colors_layout.addLayout(colors_grid)
        layout.addWidget(colors_card)
        
        # Кнопки действий
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(8)
        
        self.save_config_btn = PushButton("Сохранить конфигурацию", content)
        self.save_config_btn.setMinimumHeight(36)
        
        self.apply_btn = PrimaryPushButton("Применить настройки", content)
        self.apply_btn.setMinimumHeight(36)
        
        actions_layout.addWidget(self.save_config_btn)
        actions_layout.addWidget(self.apply_btn)
        actions_layout.addStretch()
        
        layout.addLayout(actions_layout)
        layout.addStretch()
        
        # Устанавливаем содержимое в scroll
        scroll.setWidget(content)
        main_layout.addWidget(scroll)
        
        # Подключение сигналов
        self.sqlite_radio.toggled.connect(self._on_source_changed)
        self.files_radio.toggled.connect(self._on_source_changed)
        
        # Инициализация видимости
        self._on_source_changed()
        
        # Завершение инициализации
        self._initializing = False
    
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
    
    def _reset_colors(self):
        """Сбросить цвета к дефолтным значениям"""
        self.neutral_picker.setColor(QColor("#FFFFFF"))
        self.warning_picker.setColor(QColor("#FFA500"))
        self.error_picker.setColor(QColor("#FF0000"))
        self.success_picker.setColor(QColor("#00B050"))
        self.info_picker.setColor(QColor("#FFFF00"))
        
        InfoBar.success(
            "Цвета сброшены",
            "Цветовая схема сброшена к дефолтным значениям",
            parent=self,
            duration=2000,
            position=InfoBarPosition.TOP_RIGHT
        )
    
    def get_color_scheme_dict(self):
        """
        Получить текущую цветовую схему в виде словаря
        
        Returns:
            dict: Словарь с цветами в HEX формате
        """
        return {
            'neutral': self.neutral_picker.color.name()[1:].upper(),
            'warning': self.warning_picker.color.name()[1:].upper(),
            'error': self.error_picker.color.name()[1:].upper(),
            'success': self.success_picker.color.name()[1:].upper(),
            'info': self.info_picker.color.name()[1:].upper()
        }
    
    def set_color_scheme(self, scheme):
        """
        Установить цветовую схему из ColorScheme
        
        Args:
            scheme: ColorScheme объект
        """
        self.neutral_picker.setColor(QColor(f"#{scheme.neutral}"))
        self.warning_picker.setColor(QColor(f"#{scheme.warning}"))
        self.error_picker.setColor(QColor(f"#{scheme.error}"))
        self.success_picker.setColor(QColor(f"#{scheme.success}"))
        self.info_picker.setColor(QColor(f"#{scheme.info}"))
    
    def _refresh_cameras(self):
        """Обновить список доступных камер из загруженных данных"""
        # Очищаем текущие чекбоксы
        self._clear_camera_checkboxes()
        
        # Получаем список камер из состояния приложения
        cameras = self._get_available_cameras()
        
        if not cameras:
            InfoBar.warning(
                "Нет данных",
                "Загрузите данные для определения доступных камер",
                parent=self,
                duration=3000,
                position=InfoBarPosition.TOP_RIGHT
            )
            return
        
        # Создаем чекбоксы для каждой камеры
        for camera_ip, camera_name in cameras.items():
            # Чекбокс для прихода
            arrival_check = CheckBox(f"{camera_name} ({camera_ip})", self)
            self.arrival_camera_checks[camera_ip] = arrival_check
            self.arrival_cameras_layout.addWidget(arrival_check)
            
            # Чекбокс для ухода
            departure_check = CheckBox(f"{camera_name} ({camera_ip})", self)
            self.departure_camera_checks[camera_ip] = departure_check
            self.departure_cameras_layout.addWidget(departure_check)
        
        InfoBar.success(
            "Камеры обновлены",
            f"Найдено камер: {len(cameras)}",
            parent=self,
            duration=2000,
            position=InfoBarPosition.TOP_RIGHT
        )
    
    def _clear_camera_checkboxes(self):
        """Очистить все чекбоксы камер"""
        # Удаляем виджеты для прихода
        for checkbox in self.arrival_camera_checks.values():
            self.arrival_cameras_layout.removeWidget(checkbox)
            checkbox.deleteLater()
        self.arrival_camera_checks.clear()
        
        # Удаляем виджеты для ухода
        for checkbox in self.departure_camera_checks.values():
            self.departure_cameras_layout.removeWidget(checkbox)
            checkbox.deleteLater()
        self.departure_camera_checks.clear()
    
    def _get_available_cameras(self):
        """
        Получить список доступных камер из загруженных данных
        
        Returns:
            dict: Словарь {camera_ip: camera_name}
        """
        try:
            from services.data_loader import DataLoader
            
            # Получаем главное окно для доступа к state
            main_window = self.window()
            if not hasattr(main_window, 'state'):
                return {}
            
            # Определяем источник данных
            state = main_window.state
            
            if state.data_source_type == 'sqlite':
                if not state.sqlite_path:
                    return {}
                data_source = state.sqlite_path
                file_type = 'sqlite'
            else:
                if not state.files:
                    return {}
                data_source = state.files
                file_type = None
            
            # Загружаем данные
            df = DataLoader.load_logs(data_source, file_type=file_type)
            
            # Проверяем наличие колонок _device и _device_name
            if '_device' not in df.columns:
                return {}
            
            # Извлекаем уникальные камеры
            cameras = {}
            
            if '_device_name' in df.columns:
                # Создаём словарь IP -> Имя
                unique_devices = (
                    df[['_device', '_device_name']].drop_duplicates()
                )
                for _, row in unique_devices.iterrows():
                    device_ip = row['_device']
                    device_name = row['_device_name']
                    if device_ip and str(device_ip) != 'nan':
                        cameras[device_ip] = (
                            device_name if device_name else device_ip
                        )
            else:
                # Только IP адреса
                unique_devices = df['_device'].dropna().unique()
                for device_ip in unique_devices:
                    cameras[device_ip] = device_ip
            
            return cameras
            
        except Exception as e:
            print(f"Ошибка при получении списка камер: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def get_device_mapping(self):
        """
        Получить текущую настройку device_mapping
        
        Returns:
            dict | None: Словарь с arrival_devices и departure_devices или None
        """
        arrival_devices = [
            ip for ip, checkbox in self.arrival_camera_checks.items()
            if checkbox.isChecked()
        ]
        departure_devices = [
            ip for ip, checkbox in self.departure_camera_checks.items()
            if checkbox.isChecked()
        ]
        
        # Если ничего не выбрано, возвращаем None (отключаем фильтрацию)
        if not arrival_devices and not departure_devices:
            return None
        
        return {
            'arrival_devices': arrival_devices,
            'departure_devices': departure_devices
        }
    
    def set_device_mapping(self, device_mapping):
        """
        Установить device_mapping в UI
        
        Args:
            device_mapping: dict с ключами arrival_devices и departure_devices
        """
        if not device_mapping:
            return
        
        arrival_devices = device_mapping.get('arrival_devices', [])
        departure_devices = device_mapping.get('departure_devices', [])
        
        # Отмечаем соответствующие чекбоксы
        for ip, checkbox in self.arrival_camera_checks.items():
            checkbox.setChecked(ip in arrival_devices)
        
        for ip, checkbox in self.departure_camera_checks.items():
            checkbox.setChecked(ip in departure_devices)

