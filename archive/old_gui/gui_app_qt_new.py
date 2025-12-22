"""
LogStorm GUI - Qt6 версия (Windows 11 Design System)
Минимальная версия для поэтапной разработки
"""

import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QPushButton, QLineEdit, QGroupBox,
    QListWidget, QCheckBox, QRadioButton, QButtonGroup, QFileDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class LogStormQt(QMainWindow):
    """Главное окно приложения"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LogStorm")
        self.setGeometry(100, 100, 1000, 700)
        
        # Определяем тему
        self.is_dark_theme = self._detect_dark_theme()
        
        self._init_ui()
        self._apply_windows11_style()
    
    def _detect_dark_theme(self):
        """Определить тему Windows"""
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            )
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            return value == 0
        except Exception:
            return False
    
    def _init_ui(self):
        """Инициализация UI"""
        # Центральный виджет
        central = QWidget()
        self.setCentralWidget(central)
        
        # Главный layout
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Вкладки
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        main_layout.addWidget(self.tabs)
        
        # Пока только одна вкладка
        settings_tab = self._create_settings_tab()
        self.tabs.addTab(settings_tab, "Настройки")
    
    def _create_settings_tab(self):
        """Создать вкладку настроек"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Стандартные отступы Windows 11: 12px по краям
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Группа: Файлы
        files_group = QGroupBox("Файлы логов")
        files_layout = QVBoxLayout()
        files_layout.setSpacing(8)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)
        
        add_btn = QPushButton("Добавить файл")
        add_btn.clicked.connect(self._add_file)
        
        clear_btn = QPushButton("Очистить")
        clear_btn.setProperty("secondary", True)
        
        buttons_layout.addWidget(add_btn)
        buttons_layout.addWidget(clear_btn)
        buttons_layout.addStretch()
        
        files_layout.addLayout(buttons_layout)
        
        # Список файлов
        self.files_list = QListWidget()
        self.files_list.setMaximumHeight(120)
        files_layout.addWidget(self.files_list)
        
        files_group.setLayout(files_layout)
        layout.addWidget(files_group)
        
        # Группа: Опции
        options_group = QGroupBox("Опции")
        options_layout = QVBoxLayout()
        options_layout.setSpacing(8)
        
        self.ai_check = QCheckBox("Использовать AI анализ")
        self.ai_check.setChecked(True)
        options_layout.addWidget(self.ai_check)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Кнопка применить
        apply_btn = QPushButton("Применить")
        apply_btn.setMinimumHeight(32)
        layout.addWidget(apply_btn)
        
        layout.addStretch()
        
        return widget
    
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
    
    def _apply_windows11_style(self):
        """Применить стили Windows 11"""
        
        if self.is_dark_theme:
            self._apply_dark_theme()
        else:
            self._apply_light_theme()
    
    def _apply_light_theme(self):
        """Светлая тема Windows 11"""
        self.setStyleSheet("""
            /* === WINDOWS 11 LIGHT THEME === */
            
            * {
                font-family: "Segoe UI", "Segoe UI Variable Display", sans-serif;
                font-size: 14px;
                outline: none;
            }
            
            QMainWindow {
                background-color: #F3F3F3;
            }
            
            QWidget {
                background-color: transparent;
                color: #000000;
            }
            
            /* Вкладки */
            QTabWidget::pane {
                border: none;
                background-color: transparent;
            }
            
            QTabBar {
                background-color: transparent;
            }
            
            QTabBar::tab {
                background-color: transparent;
                color: rgba(0, 0, 0, 0.8956);
                padding: 11px 12px 11px 12px;
                border: none;
                border-bottom: 2px solid transparent;
            }
            
            QTabBar::tab:hover {
                background-color: rgba(0, 0, 0, 0.0373);
                color: rgba(0, 0, 0, 0.8956);
            }
            
            QTabBar::tab:selected {
                background-color: transparent;
                color: #005FB7;
                border-bottom: 2px solid #005FB7;
            }
            
            /* Группы */
            QGroupBox {
                background-color: #FFFFFF;
                border: 1px solid rgba(0, 0, 0, 0.0578);
                border-radius: 8px;
                padding-top: 16px;
                margin-top: 8px;
                font-weight: 600;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 16px;
                padding: 0 4px;
                background-color: #FFFFFF;
                color: rgba(0, 0, 0, 0.8956);
            }
            
            /* Кнопки */
            QPushButton {
                background-color: #005FB7;
                color: #FFFFFF;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 5px 12px;
                min-height: 32px;
            }
            
            QPushButton:hover {
                background-color: #0078D4;
            }
            
            QPushButton:pressed {
                background-color: #004C87;
            }
            
            QPushButton:disabled {
                background-color: rgba(0, 0, 0, 0.0373);
                color: rgba(0, 0, 0, 0.3614);
            }
            
            QPushButton[secondary="true"] {
                background-color: rgba(0, 0, 0, 0.0373);
                color: rgba(0, 0, 0, 0.8956);
                border: 1px solid rgba(0, 0, 0, 0.0578);
            }
            
            QPushButton[secondary="true"]:hover {
                background-color: rgba(0, 0, 0, 0.0578);
            }
            
            QPushButton[secondary="true"]:pressed {
                background-color: rgba(0, 0, 0, 0.0241);
                color: rgba(0, 0, 0, 0.6063);
            }
            
            /* Поля ввода */
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid rgba(0, 0, 0, 0.0578);
                border-bottom: 1px solid rgba(0, 0, 0, 0.3614);
                border-radius: 4px;
                padding: 5px 12px;
                min-height: 32px;
                selection-background-color: #0078D4;
                selection-color: #FFFFFF;
            }
            
            QLineEdit:hover {
                border-bottom-color: rgba(0, 0, 0, 0.6063);
            }
            
            QLineEdit:focus {
                border-color: #0078D4;
                border-bottom-width: 2px;
                padding-bottom: 4px;
            }
            
            /* Списки */
            QListWidget {
                background-color: #FFFFFF;
                border: 1px solid rgba(0, 0, 0, 0.0578);
                border-radius: 4px;
                padding: 4px;
            }
            
            QListWidget::item {
                border-radius: 4px;
                padding: 8px;
            }
            
            QListWidget::item:hover {
                background-color: rgba(0, 0, 0, 0.0373);
            }
            
            QListWidget::item:selected {
                background-color: rgba(0, 95, 183, 0.1490);
                color: rgba(0, 0, 0, 0.8956);
            }
            
            /* Чекбоксы */
            QCheckBox {
                spacing: 8px;
                color: rgba(0, 0, 0, 0.8956);
            }
            
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 1px solid rgba(0, 0, 0, 0.6063);
                border-radius: 4px;
                background-color: #FFFFFF;
            }
            
            QCheckBox::indicator:hover {
                border-color: #0078D4;
                background-color: rgba(0, 0, 0, 0.0373);
            }
            
            QCheckBox::indicator:checked {
                background-color: #0078D4;
                border-color: #0078D4;
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iMTIiIHZpZXdCb3g9IjAgMCAxMiAxMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cGF0aCBkPSJNMTAgM0w0LjUgOC41TDIgNiIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSIxLjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPjwvc3ZnPg==);
            }
            
            /* Скроллбары */
            QScrollBar:vertical {
                background-color: transparent;
                width: 12px;
                margin: 0px;
            }
            
            QScrollBar::handle:vertical {
                background-color: rgba(0, 0, 0, 0.2169);
                border-radius: 6px;
                min-height: 40px;
                margin: 2px;
            }
            
            QScrollBar::handle:vertical:hover {
                background-color: rgba(0, 0, 0, 0.3614);
            }
            
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: none;
                border: none;
                height: 0px;
            }
        """)
    
    def _apply_dark_theme(self):
        """Темная тема Windows 11"""
        self.setStyleSheet("""
            /* === WINDOWS 11 DARK THEME === */
            
            * {
                font-family: "Segoe UI", "Segoe UI Variable Display", sans-serif;
                font-size: 14px;
                outline: none;
            }
            
            QMainWindow {
                background-color: #202020;
            }
            
            QWidget {
                background-color: transparent;
                color: #FFFFFF;
            }
            
            /* Вкладки */
            QTabWidget::pane {
                border: none;
                background-color: transparent;
            }
            
            QTabBar {
                background-color: transparent;
            }
            
            QTabBar::tab {
                background-color: transparent;
                color: rgba(255, 255, 255, 0.8956);
                padding: 11px 12px 11px 12px;
                border: none;
                border-bottom: 2px solid transparent;
            }
            
            QTabBar::tab:hover {
                background-color: rgba(255, 255, 255, 0.0605);
                color: rgba(255, 255, 255, 0.8956);
            }
            
            QTabBar::tab:selected {
                background-color: transparent;
                color: #60CDFF;
                border-bottom: 2px solid #60CDFF;
            }
            
            /* Группы */
            QGroupBox {
                background-color: rgba(255, 255, 255, 0.0605);
                border: 1px solid rgba(255, 255, 255, 0.0837);
                border-radius: 8px;
                padding-top: 16px;
                margin-top: 8px;
                font-weight: 600;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 16px;
                padding: 0 4px;
                background-color: rgba(255, 255, 255, 0.0605);
                color: rgba(255, 255, 255, 0.8956);
            }
            
            /* Кнопки */
            QPushButton {
                background-color: #60CDFF;
                color: #000000;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 5px 12px;
                min-height: 32px;
            }
            
            QPushButton:hover {
                background-color: #8ADDFF;
            }
            
            QPushButton:pressed {
                background-color: #3AA0C9;
            }
            
            QPushButton:disabled {
                background-color: rgba(255, 255, 255, 0.0605);
                color: rgba(255, 255, 255, 0.3628);
            }
            
            QPushButton[secondary="true"] {
                background-color: rgba(255, 255, 255, 0.0605);
                color: rgba(255, 255, 255, 0.8956);
                border: 1px solid rgba(255, 255, 255, 0.0837);
            }
            
            QPushButton[secondary="true"]:hover {
                background-color: rgba(255, 255, 255, 0.0837);
            }
            
            QPushButton[secondary="true"]:pressed {
                background-color: rgba(255, 255, 255, 0.0326);
                color: rgba(255, 255, 255, 0.6063);
            }
            
            /* Поля ввода */
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.0605);
                border: 1px solid rgba(255, 255, 255, 0.0837);
                border-bottom: 1px solid rgba(255, 255, 255, 0.4458);
                border-radius: 4px;
                padding: 5px 12px;
                min-height: 32px;
                color: #FFFFFF;
                selection-background-color: #60CDFF;
                selection-color: #000000;
            }
            
            QLineEdit:hover {
                border-bottom-color: rgba(255, 255, 255, 0.6063);
            }
            
            QLineEdit:focus {
                border-color: #60CDFF;
                border-bottom-width: 2px;
                padding-bottom: 4px;
            }
            
            /* Списки */
            QListWidget {
                background-color: rgba(255, 255, 255, 0.0605);
                border: 1px solid rgba(255, 255, 255, 0.0837);
                border-radius: 4px;
                padding: 4px;
                color: #FFFFFF;
            }
            
            QListWidget::item {
                border-radius: 4px;
                padding: 8px;
            }
            
            QListWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.0837);
            }
            
            QListWidget::item:selected {
                background-color: rgba(96, 205, 255, 0.1490);
                color: rgba(255, 255, 255, 0.8956);
            }
            
            /* Чекбоксы */
            QCheckBox {
                spacing: 8px;
                color: rgba(255, 255, 255, 0.8956);
            }
            
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 1px solid rgba(255, 255, 255, 0.6063);
                border-radius: 4px;
                background-color: rgba(255, 255, 255, 0.0605);
            }
            
            QCheckBox::indicator:hover {
                border-color: #60CDFF;
                background-color: rgba(255, 255, 255, 0.0837);
            }
            
            QCheckBox::indicator:checked {
                background-color: #60CDFF;
                border-color: #60CDFF;
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iMTIiIHZpZXdCb3g9IjAgMCAxMiAxMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cGF0aCBkPSJNMTAgM0w0LjUgOC41TDIgNiIgc3Ryb2tlPSJibGFjayIgc3Ryb2tlLXdpZHRoPSIxLjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPjwvc3ZnPg==);
            }
            
            /* Скроллбары */
            QScrollBar:vertical {
                background-color: transparent;
                width: 12px;
                margin: 0px;
            }
            
            QScrollBar::handle:vertical {
                background-color: rgba(255, 255, 255, 0.2169);
                border-radius: 6px;
                min-height: 40px;
                margin: 2px;
            }
            
            QScrollBar::handle:vertical:hover {
                background-color: rgba(255, 255, 255, 0.3614);
            }
            
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: none;
                border: none;
                height: 0px;
            }
        """)


def main():
    """Запуск приложения"""
    app = QApplication(sys.argv)
    
    # Используем Segoe UI шрифт
    font = QFont("Segoe UI", 14)
    app.setFont(font)
    
    window = LogStormQt()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
