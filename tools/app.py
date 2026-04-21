#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LogStorm GUI - Графический интерфейс на PySide6 (Qt6)
"""

import os
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QPushButton, QLabel, QLineEdit, QTextEdit,
    QFileDialog, QMessageBox, QCheckBox, QRadioButton, QButtonGroup,
    QGroupBox, QListWidget, QProgressBar, QStatusBar
)
from PySide6.QtCore import Qt, QThread, Signal, QSize, QSettings
from PySide6.QtGui import QFont, QIcon, QPalette, QColor

from services import DataLoader, AttendanceService, PersonMapper
from reporters import SummaryReporter, ExcelReporter, ExcelFormatter

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# Константы
WINDOW_TITLE = "🔍 LogStorm v3.0 - Анализ посещаемости"
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
DEFAULT_CSV_PATH = "data/attendance.csv"
DEFAULT_PREFS_PATH = "person_prefs.json"
DEFAULT_OUTPUT_PATH = "reports/attendance_report.xlsx"


class AnalysisWorker(QThread):
    """Рабочий поток для анализа"""
    log_signal = Signal(str)
    status_signal = Signal(str)
    finished_signal = Signal(bool, str)
    
    def __init__(self, logs_paths, prefs_path, mapping_path, output_path, 
                 file_type):
        super().__init__()
        self.logs_paths = logs_paths
        self.prefs_path = prefs_path
        self.mapping_path = mapping_path
        self.output_path = output_path
        self.file_type = file_type
    
    def run(self):
        """Основная логика анализа"""
        try:
            self.log_signal.emit("="*60)
            self.log_signal.emit("LogStorm - Запуск анализа")
            self.log_signal.emit(f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.log_signal.emit("="*60 + "\n")
            
            # 1. Загрузка данных
            self.log_signal.emit("[1/5] 📂 Загрузка данных...")
            self.status_signal.emit("⏳ Загрузка данных...")
            
            # Загрузка PersonMapper для NDJSON (опционально)
            person_mapper = None
            if self.mapping_path and os.path.exists(self.mapping_path):
                try:
                    person_mapper = PersonMapper(self.mapping_path)
                    self.log_signal.emit(f"✅ Загружен маппинг: {self.mapping_path}")
                    self.log_signal.emit(f"   Сотрудников: {len(person_mapper.mappings)}")
                    self.log_signal.emit(f"   Алиасов: {len(person_mapper.aliases)}")
                except Exception as e:
                    self.log_signal.emit(f"⚠️ Ошибка загрузки маппинга: {e}")
                    person_mapper = None
            
            # Загрузка логов
            if len(self.logs_paths) == 1:
                self.log_signal.emit(f"Файл: {os.path.basename(self.logs_paths[0])}")
                df = DataLoader.load_logs(
                    self.logs_paths[0],
                    file_type=self.file_type,
                    person_mapper=person_mapper
                )
            else:
                self.log_signal.emit(f"Файлов: {len(self.logs_paths)}")
                df = DataLoader.load_logs(
                    self.logs_paths,
                    file_type=self.file_type,
                    person_mapper=person_mapper
                )
            
            # Загрузка профилей
            if self.prefs_path and os.path.exists(self.prefs_path):
                prefs = DataLoader.load_preferences(self.prefs_path)
            else:
                if person_mapper:
                    prefs = person_mapper.convert_to_prefs_format()
                    self.log_signal.emit("✅ Расписания загружены из маппинга")
                else:
                    prefs = {}
                    self.log_signal.emit("⚠️ Профили не используются - дефолтные настройки")
            
            self.log_signal.emit(
                f"✅ Загружено {len(df)} записей, "
                f"{len(prefs)} профилей\n"
            )
            
            df = DataLoader.filter_known_users(df, prefs)
            
            # 2. Анализ
            self.log_signal.emit("\n[2/5] 🔍 Анализ посещаемости...")
            self.status_signal.emit("⏳ Анализ посещаемости...")
            service = AttendanceService(df, prefs)
            records = service.analyze_all()
            self.log_signal.emit(f"✅ Проанализировано {len(records)} записей\n")
            
            # 3. Сводка
            self.log_signal.emit("\n[3/5] 📊 Генерация сводки...")
            self.status_signal.emit("⏳ Генерация сводки...")
            summary = SummaryReporter(records)
            summary.print_summary()
            self.log_signal.emit("✅ Сводка готова\n")
            
            # 4. Excel
            self.log_signal.emit("\n[4/5] 📝 Создание Excel отчёта...")
            self.status_signal.emit("⏳ Создание Excel отчёта...")
            os.makedirs(os.path.dirname(self.output_path) or '.', exist_ok=True)
            excel_reporter = ExcelReporter(records)
            success = excel_reporter.generate_report(self.output_path)
            
            if success:
                formatter = ExcelFormatter(self.output_path, excel_reporter)
                formatter.format_all()
                self.log_signal.emit(f"✅ Отчёт сохранён: {self.output_path}\n")
            else:
                self.log_signal.emit("❌ Ошибка создания отчёта\n")
            
            self.log_signal.emit("\n" + "="*60)
            self.log_signal.emit("✅ АНАЛИЗ ЗАВЕРШЁН УСПЕШНО!")
            self.log_signal.emit("="*60)
            
            self.finished_signal.emit(True, self.output_path)
            
        except Exception as e:
            error_msg = f"❌ ОШИБКА: {str(e)}"
            self.log_signal.emit(f"\n{error_msg}")
            self.finished_signal.emit(False, str(e))


class LogStormQt(QMainWindow):
    """Главное окно приложения"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        
        # Переменные
        self.logs_paths = [DEFAULT_CSV_PATH]
        self.prefs_path = DEFAULT_PREFS_PATH
        self.mapping_path = ""
        self.output_path = DEFAULT_OUTPUT_PATH
        self.file_type = "auto"
        self.is_running = False
        self.worker = None
        
        # Определяем тему системы
        self.is_dark_theme = self._detect_dark_theme()
        
        self._init_ui()
        self._check_files()
    
    def _detect_dark_theme(self):
        """Определить, используется ли тёмная тема Windows"""
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            )
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            # 0 = тёмная тема, 1 = светлая тема
            return value == 0
        except Exception:
            # По умолчанию светлая тема
            return False
    
    def _init_ui(self):
        """Инициализация интерфейса"""
        # Применяем Mica эффект для Windows 11
        try:
            from ctypes import windll, c_int, byref
            hwnd = int(self.winId())
            # DWM_SYSTEMBACKDROP_TYPE
            DWMWA_SYSTEMBACKDROP_TYPE = 38
            DWMSBT_MAINWINDOW = 2  # Mica
            windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_SYSTEMBACKDROP_TYPE,
                byref(c_int(DWMSBT_MAINWINDOW)),
                4
            )
        except Exception:
            pass  # Если не Windows 11, игнорируем
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Вкладки (будут интегрированы в title bar визуально)
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)  # Убирает рамку вкладок
        layout.addWidget(self.tabs)
        
        # Вкладка 1: Настройки
        self.settings_tab = self._create_settings_tab()
        self.tabs.addTab(self.settings_tab, "Настройки")
        
        # Вкладка 2: Сотрудники
        self.persons_tab = self._create_persons_tab()
        self.tabs.addTab(self.persons_tab, "Сотрудники")
        
        # Вкладка 3: Экспорт логов
        self.export_tab = self._create_export_tab()
        self.tabs.addTab(self.export_tab, "Экспорт")
        
        # Вкладка 4: Анализ
        self.analysis_tab = self._create_analysis_tab()
        self.tabs.addTab(self.analysis_tab, "Анализ")
        
        # Вкладка 5: О программе
        self.about_tab = self._create_about_tab()
        self.tabs.addTab(self.about_tab, "О программе")
        
        # Статус-бар
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готов к работе")
        
        # Прогресс-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        # Применяем стили
        self._apply_styles()
    
    def _apply_styles(self):
        """Применить современные стили Qt с поддержкой темы"""
        
        if self.is_dark_theme:
            self._apply_dark_theme()
        else:
            self._apply_light_theme()
    
    def _apply_light_theme(self):
        """Светлая тема Windows 11"""
        self.setStyleSheet("""
            * {
                font-family: "Segoe UI", "Segoe UI Variable", sans-serif;
                font-size: 9pt;
                outline: none;
            }
            
            QMainWindow {
                background-color: rgba(243, 243, 243, 0.9);
            }
            
            QWidget {
                background-color: transparent;
                color: #1c1c1c;
            }
            
            /* Вкладки - интегрированы в окно как в Windows 11 */
            QTabWidget::pane {
                border: none;
                background-color: transparent;
                margin-top: 0px;
            }
            
            QTabBar {
                background-color: transparent;
                border: none;
            }
            
            QTabBar::tab {
                background-color: transparent;
                color: #1c1c1c;
                padding: 8px 16px;
                margin: 0px 0px 0px 0px;
                border: none;
                border-bottom: 2px solid transparent;
                min-width: 80px;
            }
            
            QTabBar::tab:hover {
                background-color: rgba(0, 0, 0, 0.03);
            }
            
            QTabBar::tab:selected {
                background-color: transparent;
                color: #005fb8;
                border-bottom: 2px solid #005fb8;
                font-weight: 600;
            }
            
            QTabBar::tab:first {
                margin-left: 12px;
            }
            
            /* Группы */
            QGroupBox {
                font-weight: 600;
                color: #1c1c1c;
                border: 1px solid #ededed;
                border-radius: 8px;
                margin-top: 6px;
                padding-top: 16px;
                background-color: rgba(255, 255, 255, 0.7);
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 12px;
                padding: 0 4px;
                background-color: #fafafa;
            }
            
            /* Кнопки - Primary */
            QPushButton {
                background-color: #005fb8;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 4px;
                min-height: 32px;
            }
            
            QPushButton:hover {
                background-color: #0067c7;
            }
            
            QPushButton:pressed {
                background-color: #004a8f;
            }
            
            QPushButton:disabled {
                background-color: #f3f3f3;
                color: rgba(0, 0, 0, 0.36);
            }
            
            /* Кнопки - Secondary */
            QPushButton[class="secondary"] {
                background-color: #f3f3f3;
                color: #1c1c1c;
                border: 1px solid #d1d1d1;
            }
            
            QPushButton[class="secondary"]:hover {
                background-color: #e9e9e9;
                border-color: #adadad;
            }
            
            QPushButton[class="secondary"]:pressed {
                background-color: #d9d9d9;
            }
            
            /* Кнопки - Danger */
            QPushButton[class="danger"] {
                background-color: #c42b1c;
                border: none;
            }
            
            QPushButton[class="danger"]:hover {
                background-color: #d13438;
            }
            
            /* Поля ввода */
            QLineEdit {
                padding: 8px 12px;
                border: 1px solid #8a8a8a;
                border-bottom-width: 1px;
                border-radius: 4px;
                background-color: #ffffff;
                min-height: 32px;
                selection-background-color: #005fb8;
                selection-color: white;
            }
            
            QLineEdit:hover {
                border-bottom-color: #1c1c1c;
            }
            
            QLineEdit:focus {
                border-color: #005fb8;
                border-bottom-width: 2px;
            }
            
            QLineEdit:disabled {
                background-color: #f9f9f9;
                color: rgba(0, 0, 0, 0.36);
                border-color: #d1d1d1;
            }
            
            /* Текстовые области */
            QTextEdit {
                border: 1px solid #8a8a8a;
                border-radius: 4px;
                background-color: #ffffff;
                padding: 8px;
                selection-background-color: #005fb8;
                selection-color: white;
            }
            
            QTextEdit:hover {
                border-color: #1c1c1c;
            }
            
            QTextEdit:focus {
                border: 2px solid #005fb8;
                padding: 7px;
            }
            
            /* Списки */
            QListWidget {
                border: 1px solid #8a8a8a;
                border-radius: 4px;
                background-color: #ffffff;
                padding: 4px;
            }
            
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
            }
            
            QListWidget::item:hover {
                background-color: rgba(0, 0, 0, 0.04);
            }
            
            QListWidget::item:selected {
                background-color: rgba(0, 95, 184, 0.1);
                color: #1c1c1c;
            }
            
            /* Чекбоксы */
            QCheckBox {
                spacing: 8px;
            }
            
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #8a8a8a;
                border-radius: 4px;
                background-color: #ffffff;
            }
            
            QCheckBox::indicator:hover {
                border-color: #1c1c1c;
                background-color: #f9f9f9;
            }
            
            QCheckBox::indicator:checked {
                background-color: #005fb8;
                border-color: #005fb8;
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iMTIiIHZpZXdCb3g9IjAgMCAxMiAxMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cGF0aCBkPSJNMTAgM0w0LjUgOC41TDIgNiIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz48L3N2Zz4=);
            }
            
            /* Радиокнопки */
            QRadioButton {
                spacing: 8px;
            }
            
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #8a8a8a;
                border-radius: 10px;
                background-color: #ffffff;
            }
            
            QRadioButton::indicator:hover {
                border-color: #1c1c1c;
                background-color: #f9f9f9;
            }
            
            QRadioButton::indicator:checked {
                border: 6px solid #005fb8;
                background-color: #ffffff;
            }
            
            /* Прогресс-бар */
            QProgressBar {
                border: none;
                border-radius: 2px;
                background-color: #e6e6e6;
                text-align: center;
                min-height: 4px;
                max-height: 4px;
            }
            
            QProgressBar::chunk {
                background-color: #005fb8;
                border-radius: 2px;
            }
            
            /* Статус-бар */
            QStatusBar {
                background-color: #f9f9f9;
                color: #1c1c1c;
                border-top: 1px solid #ededed;
            }
            
            /* Скроллбары */
            QScrollBar:vertical {
                background-color: transparent;
                width: 12px;
                margin: 0px;
            }
            
            QScrollBar::handle:vertical {
                background-color: rgba(0, 0, 0, 0.3);
                border-radius: 6px;
                min-height: 30px;
                margin: 2px;
            }
            
            QScrollBar::handle:vertical:hover {
                background-color: rgba(0, 0, 0, 0.5);
            }
            
            QScrollBar::add-line:vertical, 
            QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: none;
                border: none;
                height: 0px;
            }
            
            QScrollBar:horizontal {
                background-color: transparent;
                height: 12px;
                margin: 0px;
            }
            
            QScrollBar::handle:horizontal {
                background-color: rgba(0, 0, 0, 0.3);
                border-radius: 6px;
                min-width: 30px;
                margin: 2px;
            }
            
            QScrollBar::handle:horizontal:hover {
                background-color: rgba(0, 0, 0, 0.5);
            }
            
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal,
            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {
                background: none;
                border: none;
                width: 0px;
            }
        """)
    
    def _apply_dark_theme(self):
        """Темная тема Windows 11"""
        self.setStyleSheet("""
            * {
                font-family: "Segoe UI", "Segoe UI Variable", sans-serif;
                font-size: 9pt;
                outline: none;
            }
            
            QMainWindow {
                background-color: rgba(32, 32, 32, 0.9);
            }
            
            QWidget {
                background-color: transparent;
                color: #ffffff;
            }
            
            /* Вкладки - интегрированы в окно как в Windows 11 Dark */
            QTabWidget::pane {
                border: none;
                background-color: transparent;
                margin-top: 0px;
            }
            
            QTabBar {
                background-color: transparent;
                border: none;
            }
            
            QTabBar::tab {
                background-color: transparent;
                color: #ffffff;
                padding: 8px 16px;
                margin: 0px 0px 0px 0px;
                border: none;
                border-bottom: 2px solid transparent;
                min-width: 80px;
            }
            
            QTabBar::tab:hover {
                background-color: rgba(255, 255, 255, 0.05);
            }
            
            QTabBar::tab:selected {
                background-color: transparent;
                color: #60cdff;
                border-bottom: 2px solid #60cdff;
                font-weight: 600;
            }
            
            QTabBar::tab:first {
                margin-left: 12px;
            }
            
            /* Группы */
            QGroupBox {
                font-weight: 600;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                border-radius: 8px;
                margin-top: 6px;
                padding-top: 16px;
                background-color: rgba(43, 43, 43, 0.7);
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 12px;
                padding: 0 4px;
                background-color: #2b2b2b;
            }
            
            /* Кнопки - Primary */
            QPushButton {
                background-color: #60cdff;
                color: #000000;
                border: none;
                padding: 8px 12px;
                border-radius: 4px;
                min-height: 32px;
            }
            
            QPushButton:hover {
                background-color: #74d4ff;
            }
            
            QPushButton:pressed {
                background-color: #4cc2f5;
            }
            
            QPushButton:disabled {
                background-color: #2b2b2b;
                color: rgba(255, 255, 255, 0.36);
            }
            
            /* Кнопки - Secondary */
            QPushButton[class="secondary"] {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #4a4a4a;
            }
            
            QPushButton[class="secondary"]:hover {
                background-color: #333333;
                border-color: #5a5a5a;
            }
            
            QPushButton[class="secondary"]:pressed {
                background-color: #404040;
            }
            
            /* Кнопки - Danger */
            QPushButton[class="danger"] {
                background-color: #ff6b6b;
                color: #000000;
                border: none;
            }
            
            QPushButton[class="danger"]:hover {
                background-color: #ff7c7c;
            }
            
            /* Поля ввода */
            QLineEdit {
                padding: 8px 12px;
                border: 1px solid #5a5a5a;
                border-bottom-width: 1px;
                border-radius: 4px;
                background-color: #1c1c1c;
                color: #ffffff;
                min-height: 32px;
                selection-background-color: #60cdff;
                selection-color: #000000;
            }
            
            QLineEdit:hover {
                border-bottom-color: #ffffff;
            }
            
            QLineEdit:focus {
                border-color: #60cdff;
                border-bottom-width: 2px;
            }
            
            QLineEdit:disabled {
                background-color: #202020;
                color: rgba(255, 255, 255, 0.36);
                border-color: #4a4a4a;
            }
            
            /* Текстовые области */
            QTextEdit {
                border: 1px solid #5a5a5a;
                border-radius: 4px;
                background-color: #1c1c1c;
                color: #ffffff;
                padding: 8px;
                selection-background-color: #60cdff;
                selection-color: #000000;
            }
            
            QTextEdit:hover {
                border-color: #ffffff;
            }
            
            QTextEdit:focus {
                border: 2px solid #60cdff;
                padding: 7px;
            }
            
            /* Списки */
            QListWidget {
                border: 1px solid #5a5a5a;
                border-radius: 4px;
                background-color: #1c1c1c;
                padding: 4px;
            }
            
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
                color: #ffffff;
            }
            
            QListWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.06);
            }
            
            QListWidget::item:selected {
                background-color: rgba(96, 205, 255, 0.15);
                color: #ffffff;
            }
            
            /* Чекбоксы */
            QCheckBox {
                spacing: 8px;
                color: #ffffff;
            }
            
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #5a5a5a;
                border-radius: 4px;
                background-color: #1c1c1c;
            }
            
            QCheckBox::indicator:hover {
                border-color: #ffffff;
                background-color: #202020;
            }
            
            QCheckBox::indicator:checked {
                background-color: #60cdff;
                border-color: #60cdff;
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iMTIiIHZpZXdCb3g9IjAgMCAxMiAxMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cGF0aCBkPSJNMTAgM0w0LjUgOC41TDIgNiIgc3Ryb2tlPSJibGFjayIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz48L3N2Zz4=);
            }
            
            /* Радиокнопки */
            QRadioButton {
                spacing: 8px;
                color: #ffffff;
            }
            
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #5a5a5a;
                border-radius: 10px;
                background-color: #1c1c1c;
            }
            
            QRadioButton::indicator:hover {
                border-color: #ffffff;
                background-color: #202020;
            }
            
            QRadioButton::indicator:checked {
                border: 6px solid #60cdff;
                background-color: #1c1c1c;
            }
            
            /* Прогресс-бар */
            QProgressBar {
                border: none;
                border-radius: 2px;
                background-color: #3a3a3a;
                text-align: center;
                min-height: 4px;
                max-height: 4px;
            }
            
            QProgressBar::chunk {
                background-color: #60cdff;
                border-radius: 2px;
            }
            
            /* Статус-бар */
            QStatusBar {
                background-color: #202020;
                color: #ffffff;
                border-top: 1px solid #3a3a3a;
            }
            
            /* Скроллбары */
            QScrollBar:vertical {
                background-color: transparent;
                width: 12px;
                margin: 0px;
            }
            
            QScrollBar::handle:vertical {
                background-color: rgba(255, 255, 255, 0.3);
                border-radius: 6px;
                min-height: 30px;
                margin: 2px;
            }
            
            QScrollBar::handle:vertical:hover {
                background-color: rgba(255, 255, 255, 0.5);
            }
            
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: none;
                border: none;
                height: 0px;
            }
            
            QScrollBar:horizontal {
                background-color: transparent;
                height: 12px;
                margin: 0px;
            }
            
            QScrollBar::handle:horizontal {
                background-color: rgba(255, 255, 255, 0.3);
                border-radius: 6px;
                min-width: 30px;
                margin: 2px;
            }
            
            QScrollBar::handle:horizontal:hover {
                background-color: rgba(255, 255, 255, 0.5);
            }
            
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal,
            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {
                background: none;
                border: none;
                width: 0px;
            }
        """)
    
    def _create_settings_tab(self):
        """Создать вкладку настроек"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Файлы логов
        logs_group = QGroupBox("Файлы логов")
        logs_layout = QVBoxLayout()
        logs_layout.setSpacing(12)
        
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)
        add_btn = QPushButton("Добавить файл")
        add_btn.clicked.connect(self._add_log_file)
        clear_btn = QPushButton("Очистить")
        clear_btn.setProperty("class", "danger")
        clear_btn.clicked.connect(self._clear_log_files)
        buttons_layout.addWidget(add_btn)
        buttons_layout.addWidget(clear_btn)
        buttons_layout.addStretch()
        logs_layout.addLayout(buttons_layout)
        
        self.logs_list = QListWidget()
        self.logs_list.setMaximumHeight(100)
        logs_layout.addWidget(self.logs_list)
        
        # Тип файла
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Тип файла:"))
        self.type_group = QButtonGroup()
        self.type_auto = QRadioButton("Авто")
        self.type_csv = QRadioButton("CSV")
        self.type_ndjson = QRadioButton("NDJSON")
        self.type_auto.setChecked(True)
        self.type_group.addButton(self.type_auto, 0)
        self.type_group.addButton(self.type_csv, 1)
        self.type_group.addButton(self.type_ndjson, 2)
        type_layout.addWidget(self.type_auto)
        type_layout.addWidget(self.type_csv)
        type_layout.addWidget(self.type_ndjson)
        type_layout.addStretch()
        logs_layout.addLayout(type_layout)
        
        logs_group.setLayout(logs_layout)
        layout.addWidget(logs_group)
        
        # Профили сотрудников
        prefs_group = QGroupBox("Файл профилей сотрудников")
        prefs_layout = QHBoxLayout()
        self.prefs_edit = QLineEdit(self.prefs_path)
        self.prefs_edit.setPlaceholderText("Необязательно")
        prefs_btn = QPushButton("Обзор...")
        prefs_btn.setProperty("class", "secondary")
        prefs_btn.clicked.connect(self._browse_prefs)
        prefs_layout.addWidget(self.prefs_edit)
        prefs_layout.addWidget(prefs_btn)
        prefs_group.setLayout(prefs_layout)
        layout.addWidget(prefs_group)
        
        # Маппинг сотрудников
        mapping_group = QGroupBox("Файл маппинга сотрудников")
        mapping_layout = QHBoxLayout()
        self.mapping_edit = QLineEdit(self.mapping_path)
        self.mapping_edit.setPlaceholderText("Для NDJSON файлов")
        mapping_btn = QPushButton("Обзор...")
        mapping_btn.setProperty("class", "secondary")
        mapping_btn.clicked.connect(self._browse_mapping)
        mapping_layout.addWidget(self.mapping_edit)
        mapping_layout.addWidget(mapping_btn)
        mapping_group.setLayout(mapping_layout)
        layout.addWidget(mapping_group)
        
        # Файл отчёта
        output_group = QGroupBox("Файл отчёта Excel")
        output_layout = QHBoxLayout()
        self.output_edit = QLineEdit(self.output_path)
        output_btn = QPushButton("Обзор...")
        output_btn.setProperty("class", "secondary")
        output_btn.clicked.connect(self._browse_output)
        output_layout.addWidget(self.output_edit)
        output_layout.addWidget(output_btn)
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)
        
        # Кнопка применения
        apply_btn = QPushButton("Применить настройки")
        apply_btn.clicked.connect(self._apply_settings)
        layout.addWidget(apply_btn)
        
        layout.addStretch()
        
        self._update_logs_list()
        return widget
    
    def _create_persons_tab(self):
        """Создать вкладку управления сотрудниками"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        placeholder = QLabel(
            "Управление сотрудниками\n\n"
            "Чтобы использовать эту функцию:\n"
            "1. Перейдите на вкладку 'Настройки'\n"
            "2. Выберите файл маппинга (person_mapping.json)\n"
            "3. Нажмите 'Применить настройки'\n\n"
            "Файл маппинга позволяет:\n"
            "• Управлять расписаниями сотрудников\n"
            "• Объединять дубли через aliases\n"
            "• Импортировать данные из NDJSON"
        )
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet("color: gray; font-size: 11pt;")
        layout.addWidget(placeholder)
        
        return widget
    
    def _create_export_tab(self):
        """Создать вкладку экспорта логов"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        placeholder = QLabel(
            "📥 Экспорт логов из СКУД\n\n"
            "Функция экспорта из Hikvision/HiWatch устройств\n"
            "будет доступна в следующей версии.\n\n"
            "Пока используйте скрипт:\n"
            "python tools/export/export_acs_events.py"
        )
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet("color: gray; font-size: 11pt;")
        layout.addWidget(placeholder)
        
        return widget
    
    def _create_analysis_tab(self):
        """Создать вкладку анализа"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)
        self.run_btn = QPushButton("Запустить анализ")
        self.run_btn.clicked.connect(self._start_analysis)
        buttons_layout.addWidget(self.run_btn)
        
        hint_label = QLabel(
            "(примените настройки перед запуском)"
        )
        hint_label.setStyleSheet("color: #6c757d; font-size: 8pt;")
        buttons_layout.addWidget(hint_label)
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        # Лог
        log_group = QGroupBox("Журнал выполнения")
        log_layout = QVBoxLayout()
        log_layout.setSpacing(12)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        # Действия
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(8)
        open_btn = QPushButton("Открыть отчёт")
        open_btn.setProperty("class", "secondary")
        open_btn.clicked.connect(self._open_report)
        clear_btn = QPushButton("Очистить лог")
        clear_btn.setProperty("class", "secondary")
        clear_btn.clicked.connect(self._clear_log)
        actions_layout.addWidget(open_btn)
        actions_layout.addWidget(clear_btn)
        actions_layout.addStretch()
        layout.addLayout(actions_layout)
        
        return widget
    
    def _create_about_tab(self):
        """Создать вкладку О программе"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        about_text = QTextEdit()
        about_text.setReadOnly(True)
        about_text.setHtml("""
        <h2>🔍 LogStorm v3.0</h2>
        <p><b>Анализатор посещаемости</b></p>
        
        <h3>📌 Возможности:</h3>
        <ul>
            <li>Поддержка CSV и NDJSON форматов</li>
            <li>Умная классификация проблем</li>
            <li>Разделение технических сбоев и нарушений</li>
            <li>Цветовые Excel отчёты</li>
            <li>Управление сотрудниками через GUI</li>
        </ul>
        
        <h3>📌 Поддерживаемые устройства:</h3>
        <ul>
            <li>Камеры распознавания лиц (CSV)</li>
            <li>Hikvision/HiWatch СКУД (NDJSON)</li>
        </ul>
        
        <h3>🎨 Интерфейс:</h3>
        <p>Построен на <b>PySide6 (Qt6)</b> для современного нативного вида</p>
        
        <hr>
        <p style="color: gray;">© 2025 LogStorm Project</p>
        """)
        layout.addWidget(about_text)
        
        return widget
    
    def _update_logs_list(self):
        """Обновить список файлов логов"""
        self.logs_list.clear()
        for path in self.logs_paths:
            self.logs_list.addItem(path)
    
    def _add_log_file(self):
        """Добавить файл логов"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл логов",
            ".",
            "Log Files (*.csv *.ndjson *.json *.jsonl);;All Files (*.*)"
        )
        if filename:
            if filename not in self.logs_paths:
                self.logs_paths.append(filename)
                self._update_logs_list()
                self._log(f"✅ Добавлен файл: {os.path.basename(filename)}")
            else:
                QMessageBox.information(self, "Информация", "Этот файл уже добавлен")
    
    def _clear_log_files(self):
        """Очистить список файлов"""
        reply = QMessageBox.question(
            self, "Подтверждение", "Очистить список файлов?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.logs_paths = []
            self._update_logs_list()
            self._log("🗑️ Список файлов очищен")
    
    def _browse_prefs(self):
        """Выбор файла профилей"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл профилей", ".",
            "JSON Files (*.json);;All Files (*.*)"
        )
        if filename:
            self.prefs_edit.setText(filename)
            self._log(f"✅ Выбран файл профилей: {filename}")
    
    def _browse_mapping(self):
        """Выбор файла маппинга"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл маппинга", ".",
            "JSON Files (*.json);;All Files (*.*)"
        )
        if filename:
            self.mapping_edit.setText(filename)
            self._log(f"✅ Выбран файл маппинга: {filename}")
    
    def _browse_output(self):
        """Выбор файла вывода"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Сохранить отчёт как", ".",
            "Excel Files (*.xlsx);;All Files (*.*)"
        )
        if filename:
            self.output_edit.setText(filename)
            self._log(f"✅ Выбран файл вывода: {filename}")
    
    def _apply_settings(self):
        """Применить настройки"""
        if not self.logs_paths:
            QMessageBox.warning(self, "Нет файлов", "Добавьте хотя бы один файл логов")
            return
        
        self.prefs_path = self.prefs_edit.text()
        self.mapping_path = self.mapping_edit.text()
        self.output_path = self.output_edit.text()
        
        if self.type_auto.isChecked():
            self.file_type = "auto"
        elif self.type_csv.isChecked():
            self.file_type = "csv"
        else:
            self.file_type = "ndjson"
        
        # Обновляем вкладку сотрудников если нужно
        if self.mapping_path and self.mapping_path.strip():
            self._reload_persons_tab()
            QMessageBox.information(
                self, "Настройки применены",
                "Настройки успешно применены!\n"
                "Вкладка 'Сотрудники' обновлена.\n"
                "Можете перейти на вкладку 'Анализ' для запуска."
            )
        else:
            QMessageBox.information(
                self, "Настройки применены",
                "Настройки успешно применены!\n"
                "Файл маппинга не выбран - вкладка 'Сотрудники' недоступна.\n"
                "Можете перейти на вкладку 'Анализ' для запуска."
            )
        
        self._log("✓ Настройки применены")
        self._log(f"  - Файлов логов: {len(self.logs_paths)}")
        if self.mapping_path:
            self._log(f"  - Файл маппинга: {self.mapping_path}")
    
    def _reload_persons_tab(self):
        """Перезагрузить вкладку сотрудников"""
        # TODO: Реализовать после создания gui_person_manager_qt.py
        pass
    
    def _check_files(self):
        """Проверка существования файлов"""
        logs_exist = len(self.logs_paths) > 0 and all(
            os.path.exists(p) for p in self.logs_paths
        )
        
        if logs_exist:
            count = len(self.logs_paths)
            self._log(f"✅ Найдено {count} файл(ов) логов. Готов к запуску.")
        else:
            self._log("⚠️ Файлы логов не найдены или список пуст")
    
    def _start_analysis(self):
        """Запустить анализ"""
        if self.is_running:
            QMessageBox.warning(self, "Внимание", "Анализ уже выполняется!")
            return
        
        if not self.logs_paths:
            QMessageBox.critical(self, "Ошибка", "Не выбрано ни одного файла логов!")
            return
        
        # Проверяем существование файлов
        missing_files = [p for p in self.logs_paths if not os.path.exists(p)]
        if missing_files:
            QMessageBox.critical(
                self, "Ошибка",
                f"Не найдены файлы:\n" + "\n".join(os.path.basename(f) for f in missing_files)
            )
            return
        
        # Профили необязательны
        prefs_path = self.prefs_edit.text()
        if prefs_path and not os.path.exists(prefs_path):
            reply = QMessageBox.question(
                self, "Внимание",
                "Файл профилей не найден!\n\n"
                "Продолжить без профилей?\n"
                "Будут использованы дефолтные настройки для всех сотрудников.",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
            prefs_path = ""
        
        # Запуск анализа
        self.is_running = True
        self.run_btn.setEnabled(False)
        self.tabs.setCurrentWidget(self.analysis_tab)
        self._clear_log()
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Бесконечный режим
        self.status_bar.showMessage("⏳ Выполняется анализ...")
        
        # Создаём рабочий поток
        self.worker = AnalysisWorker(
            self.logs_paths,
            prefs_path,
            self.mapping_edit.text(),
            self.output_edit.text(),
            self.file_type
        )
        self.worker.log_signal.connect(self._log)
        self.worker.status_signal.connect(self.status_bar.showMessage)
        self.worker.finished_signal.connect(self._analysis_finished)
        self.worker.start()
    
    def _analysis_finished(self, success, message):
        """Обработка завершения анализа"""
        self.is_running = False
        self.run_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if success:
            self.status_bar.showMessage("✅ Анализ завершён")
            QMessageBox.information(
                self, "Готово",
                f"Анализ завершён!\n\nОтчёт: {message}"
            )
        else:
            self.status_bar.showMessage("❌ Ошибка")
            QMessageBox.critical(self, "Ошибка", message)
    
    def _open_report(self):
        """Открыть отчёт"""
        output_path = self.output_edit.text()
        if os.path.exists(output_path):
            os.startfile(output_path)
        else:
            QMessageBox.warning(self, "Внимание", "Отчёт ещё не создан!")
    
    def _clear_log(self):
        """Очистить лог"""
        self.log_text.clear()
    
    def _log(self, message):
        """Добавить сообщение в лог"""
        self.log_text.append(message)


def main():
    """Точка входа"""
    app = QApplication(sys.argv)
    app.setApplicationName("LogStorm")
    app.setOrganizationName("LogStorm Project")
    
    # Включаем поддержку системной темы Windows
    app.setStyle('Fusion')
    
    window = LogStormQt()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
