#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LogStorm GUI - Графический интерфейс для анализа посещаемости
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
from datetime import datetime

from gui_config import *
from services import DataLoader, AttendanceService, AIService, PersonMapper
from reporters import SummaryReporter, ExcelReporter, ExcelFormatter
from gui_export_logs import ExportLogsTab

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class LogStormGUI:
    """Главное GUI приложение"""
    
    def __init__(self, root):
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        
        # Переменные для путей
        self.logs_paths = [DEFAULT_CSV_PATH]  # Список файлов (новое!)
        self.prefs_path = tk.StringVar(value=DEFAULT_PREFS_PATH)
        self.mapping_path = tk.StringVar(value="")  # По умолчанию БЕЗ маппинга
        self.output_path = tk.StringVar(value=DEFAULT_OUTPUT_PATH)
        
        # Настройки
        self.enable_ai = tk.BooleanVar(value=True)
        self.file_type = tk.StringVar(value="auto")
        
        # Состояние
        self.is_running = False
        self.records = []
        self.person_manager = None  # Ссылка на PersonManagerTab
        
        self._setup_ui()
        self._check_files()
    
    def _setup_ui(self):
        """Настройка интерфейса"""
        # Стиль
        style = ttk.Style()
        style.theme_use('clam')
        
        # Главный контейнер
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Заголовок
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        title_label = ttk.Label(
            title_frame,
            text="🔍 LogStorm",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, 'bold')
        )
        title_label.pack(side=tk.LEFT)
        
        version_label = ttk.Label(
            title_frame,
            text="v2.0",
            font=(FONT_FAMILY, FONT_SIZE_SMALL)
        )
        version_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Notebook (вкладки)
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Вкладка 1: Настройки
        self.setup_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.setup_tab, text="⚙️ Настройки")
        self._setup_settings_tab()
        
        # Вкладка 2: Управление сотрудниками
        self.persons_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.persons_tab, text="👥 Сотрудники")
        self._setup_persons_tab()
        
        # Вкладка 3: Экспорт логов
        self.export_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.export_tab, text="📥 Экспорт логов")
        self._setup_export_tab()
        
        # Вкладка 4: Анализ
        self.analysis_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.analysis_tab, text="📊 Анализ")
        self._setup_analysis_tab()
        
        # Вкладка 5: О программе
        self.about_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.about_tab, text="ℹ️ О программе")
        self._setup_about_tab()
        
        # Нижняя панель
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.status_label = ttk.Label(
            bottom_frame,
            text="Готов к работе",
            font=(FONT_FAMILY, FONT_SIZE_SMALL)
        )
        self.status_label.pack(side=tk.LEFT)
        
        # Прогресс-бар
        self.progress = ttk.Progressbar(
            bottom_frame,
            mode='indeterminate',
            length=200
        )
        self.progress.pack(side=tk.RIGHT)
    
    def _setup_settings_tab(self):
        """Вкладка настроек"""
        # Файлы логов (множественный выбор)
        logs_frame = ttk.LabelFrame(
            self.setup_tab,
            text="📁 Файлы логов (можно выбрать несколько)",
            padding=10
        )
        logs_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Кнопки управления файлами
        buttons_frame = ttk.Frame(logs_frame)
        buttons_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(
            buttons_frame,
            text="➕ Добавить файл",
            command=self._add_log_file
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(
            buttons_frame,
            text="🗑️ Очистить всё",
            command=self._clear_log_files
        ).pack(side=tk.LEFT)
        
        # Список файлов (скроллируемый)
        list_frame = ttk.Frame(logs_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.logs_listbox = tk.Listbox(
            list_frame,
            height=4,
            yscrollcommand=scrollbar.set
        )
        self.logs_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.logs_listbox.yview)
        
        # Обновляем список
        self._update_logs_list()
        
        # Тип файла
        type_frame = ttk.Frame(logs_frame)
        type_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(
            type_frame,
            text="Тип файла:",
            font=(FONT_FAMILY, FONT_SIZE_SMALL)
        ).pack(side=tk.LEFT)
        
        ttk.Radiobutton(
            type_frame,
            text="Авто",
            variable=self.file_type,
            value="auto"
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Radiobutton(
            type_frame,
            text="CSV",
            variable=self.file_type,
            value="csv"
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Radiobutton(
            type_frame,
            text="NDJSON",
            variable=self.file_type,
            value="ndjson"
        ).pack(side=tk.LEFT, padx=5)
        
        # Файл настроек
        prefs_frame = ttk.LabelFrame(
            self.setup_tab,
            text="👤 Файл профилей сотрудников (необязательно)",
            padding=10
        )
        prefs_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Entry(
            prefs_frame,
            textvariable=self.prefs_path,
            width=60
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(
            prefs_frame,
            text="Обзор...",
            command=self._browse_prefs
        ).pack(side=tk.LEFT)
        
        # Подсказка
        hint_label = ttk.Label(
            prefs_frame,
            text="💡 Если не указан - используются дефолтные настройки",
            font=(FONT_FAMILY, FONT_SIZE_SMALL),
            foreground="gray"
        )
        hint_label.pack(anchor=tk.W, pady=(5, 0))
        
        # Файл маппинга (для NDJSON)
        mapping_frame = ttk.LabelFrame(
            self.setup_tab,
            text="🔄 Файл маппинга сотрудников (для NDJSON)",
            padding=10
        )
        mapping_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Entry(
            mapping_frame,
            textvariable=self.mapping_path,
            width=60
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(
            mapping_frame,
            text="Обзор...",
            command=self._browse_mapping
        ).pack(side=tk.LEFT)
        
        # Подсказка для маппинга
        mapping_hint_label = ttk.Label(
            mapping_frame,
            text="💡 Опционально: для объединения дублей (aliases) и управления расписаниями в NDJSON",
            font=(FONT_FAMILY, FONT_SIZE_SMALL),
            foreground="gray"
        )
        mapping_hint_label.pack(anchor=tk.W, pady=(5, 0))
        
        # Файл вывода
        output_frame = ttk.LabelFrame(
            self.setup_tab,
            text="💾 Файл отчёта Excel",
            padding=10
        )
        output_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Entry(
            output_frame,
            textvariable=self.output_path,
            width=60
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(
            output_frame,
            text="Обзор...",
            command=self._browse_output
        ).pack(side=tk.LEFT)
        
        # Опции
        options_frame = ttk.LabelFrame(
            self.setup_tab,
            text="🔧 Дополнительные опции",
            padding=10
        )
        options_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Checkbutton(
            options_frame,
            text="Включить AI анализ (GigaChat)",
            variable=self.enable_ai
        ).pack(anchor=tk.W)
        
        ttk.Label(
            options_frame,
            text="Требуется настроенный API ключ в .env файле",
            font=(FONT_FAMILY, FONT_SIZE_SMALL),
            foreground="gray"
        ).pack(anchor=tk.W, padx=(20, 0))
        
        # Кнопка применения настроек
        ttk.Button(
            self.setup_tab,
            text="✓ Применить настройки",
            command=self._apply_settings,
            style="Accent.TButton"
        ).pack(pady=20)
    
    def _setup_analysis_tab(self):
        """Вкладка анализа"""
        # Кнопка запуска анализа
        run_frame = ttk.Frame(self.analysis_tab)
        run_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(
            run_frame,
            text="▶️ Запустить анализ",
            command=self._start_analysis,
            style="Accent.TButton"
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(
            run_frame,
            text="(Перед запуском примените настройки на вкладке 'Настройки')",
            font=(FONT_FAMILY, FONT_SIZE_SMALL),
            foreground="gray"
        ).pack(side=tk.LEFT, padx=5)
        
        # Информация
        info_frame = ttk.LabelFrame(
            self.analysis_tab,
            text="📈 Информация",
            padding=10
        )
        info_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(
            info_frame,
            wrap=tk.WORD,
            font=("Consolas", 9),
            state=tk.DISABLED
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Кнопки действий
        actions_frame = ttk.Frame(self.analysis_tab)
        actions_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(
            actions_frame,
            text="📂 Открыть отчёт",
            command=self._open_report
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(
            actions_frame,
            text="🗑️ Очистить лог",
            command=self._clear_log
        ).pack(side=tk.LEFT)
    
    def _setup_persons_tab(self):
        """Вкладка управления сотрудниками"""
        # Создаём контейнер для динамической загрузки
        self.persons_container = ttk.Frame(self.persons_tab)
        self.persons_container.pack(fill=tk.BOTH, expand=True)
        
        # Показываем подсказку по умолчанию
        self._show_persons_placeholder()
    
    def _show_persons_placeholder(self):
        """Показать подсказку когда файл маппинга не выбран"""
        # Очищаем контейнер
        for widget in self.persons_container.winfo_children():
            widget.destroy()
        
        placeholder_label = ttk.Label(
            self.persons_container,
            text=(
                "👥 Управление сотрудниками\n\n"
                "Чтобы использовать эту функцию:\n"
                "1. Перейдите на вкладку 'Настройки'\n"
                "2. Выберите файл маппинга (person_mapping.json)\n"
                "3. Нажмите 'Применить настройки'\n\n"
                "Файл маппинга позволяет:\n"
                "• Управлять расписаниями сотрудников\n"
                "• Объединять дубли через aliases\n"
                "• Импортировать данные из NDJSON"
            ),
            justify=tk.CENTER,
            font=('TkDefaultFont', 10)
        )
        placeholder_label.pack(expand=True)
    
    def _reload_persons_tab(self):
        """Перезагрузить вкладку сотрудников с новым файлом"""
        from gui_person_manager import PersonManagerTab
        from config import PERSON_MAPPING_FILE
        
        # Очищаем контейнер
        for widget in self.persons_container.winfo_children():
            widget.destroy()
        
        # Проверяем, есть ли файл маппинга
        mapping_file = self.mapping_path.get()
        if not mapping_file:
            mapping_file = PERSON_MAPPING_FILE
        
        if not mapping_file or mapping_file == "":
            self._show_persons_placeholder()
            return
        
        try:
            self.person_manager = PersonManagerTab(
                self.persons_container,
                mapping_file
            )
        except Exception as e:
            error_label = ttk.Label(
                self.persons_container,
                text=(
                    f"❌ Не удалось загрузить управление сотрудниками:\n\n{e}\n\n"
                    "Убедитесь, что файл person_mapping.json существует."
                ),
                justify=tk.CENTER,
                foreground='red'
            )
            error_label.pack(expand=True)
    
    def _setup_export_tab(self):
        """Настройка вкладки экспорта логов"""
        ExportLogsTab(self.export_tab)
    
    def _setup_about_tab(self):
        """Вкладка О программе"""
        about_text = scrolledtext.ScrolledText(
            self.about_tab,
            wrap=tk.WORD,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL)
        )
        about_text.pack(fill=tk.BOTH, expand=True)
        about_text.insert(tk.END, TEXT_WELCOME)
        about_text.insert(tk.END, f"\n\n{'='*60}\n")
        about_text.insert(tk.END, "\n📌 Возможности:\n\n")
        about_text.insert(tk.END, "• Поддержка CSV и NDJSON форматов\n")
        about_text.insert(tk.END, "• Умная классификация проблем\n")
        about_text.insert(tk.END, "• Разделение технических сбоев и нарушений\n")
        about_text.insert(tk.END, "• AI анализ через GigaChat\n")
        about_text.insert(tk.END, "• Цветовые Excel отчёты\n")
        about_text.insert(tk.END, "\n📌 Поддерживаемые устройства:\n\n")
        about_text.insert(tk.END, "• Камеры распознавания лиц (CSV)\n")
        about_text.insert(tk.END, "• Hikvision/HiWatch СКУД (NDJSON)\n")
        about_text.config(state=tk.DISABLED)
    
    def _update_logs_list(self):
        """Обновить список файлов логов в GUI"""
        self.logs_listbox.delete(0, tk.END)
        for path in self.logs_paths:
            self.logs_listbox.insert(tk.END, path)
    
    def _add_log_file(self):
        """Добавить файл логов"""
        filename = filedialog.askopenfilename(
            title="Выберите файл логов",
            filetypes=FILE_TYPES_LOGS,
            initialdir="."
        )
        if filename:
            if filename not in self.logs_paths:
                self.logs_paths.append(filename)
                self._update_logs_list()
                self._log(f"✅ Добавлен файл: {os.path.basename(filename)}")
            else:
                messagebox.showinfo(
                    "Информация",
                    "Этот файл уже добавлен"
                )
    
    def _clear_log_files(self):
        """Очистить список файлов"""
        if messagebox.askyesno(
            "Подтверждение",
            "Очистить список файлов?"
        ):
            self.logs_paths = []
            self._update_logs_list()
            self._log("🗑️ Список файлов очищен")
    
    def _check_files(self):
        """Проверка существования файлов"""
        logs_exist = len(self.logs_paths) > 0 and all(
            os.path.exists(p) for p in self.logs_paths
        )
        prefs_path = self.prefs_path.get()
        prefs_exist = prefs_path and os.path.exists(prefs_path)
        
        if logs_exist:
            count = len(self.logs_paths)
            if prefs_exist:
                self._log(
                    f"✅ Найдено {count} файл(ов) логов. "
                    "Готов к запуску."
                )
            else:
                self._log(
                    f"✅ Найдено {count} файл(ов) логов. "
                    "⚠️ Профили не указаны (будут использованы дефолты)."
                )
        else:
            self._log("⚠️ Файлы логов не найдены или список пуст")
    

    
    def _browse_prefs(self):
        """Выбор файла профилей"""
        filename = filedialog.askopenfilename(
            title="Выберите файл профилей",
            filetypes=FILE_TYPES_JSON,
            initialdir="."
        )
        if filename:
            self.prefs_path.set(filename)
            self._log(f"✅ Выбран файл профилей: {filename}")
    
    def _browse_mapping(self):
        """Выбор файла маппинга"""
        filename = filedialog.askopenfilename(
            title="Выберите файл маппинга (person_mapping.json)",
            filetypes=FILE_TYPES_JSON,
            initialdir="."
        )
        if filename:
            self.mapping_path.set(filename)
            self._log(f"✅ Выбран файл маппинга: {filename}")
    
    def _browse_output(self):
        """Выбор файла вывода"""
        filename = filedialog.asksaveasfilename(
            title="Сохранить отчёт как",
            filetypes=FILE_TYPES_EXCEL,
            defaultextension=".xlsx",
            initialdir="."
        )
        if filename:
            self.output_path.set(filename)
            self._log(f"✅ Выбран файл вывода: {filename}")
    
    def _apply_settings(self):
        """Применить настройки и обновить зависимые вкладки"""
        # Проверка наличия файлов логов
        if not self.logs_paths or len(self.logs_paths) == 0:
            messagebox.showwarning(
                "Нет файлов",
                "Добавьте хотя бы один файл логов"
            )
            return
        
        # Обновляем вкладку сотрудников если выбран файл маппинга
        mapping_file = self.mapping_path.get()
        if mapping_file and mapping_file.strip():
            self._reload_persons_tab()
            messagebox.showinfo(
                "Настройки применены",
                "Настройки успешно применены!\n"
                "Вкладка 'Сотрудники' обновлена.\n"
                "Можете перейти на вкладку 'Анализ' для запуска."
            )
        else:
            messagebox.showinfo(
                "Настройки применены",
                "Настройки успешно применены!\n"
                "Файл маппинга не выбран - вкладка 'Сотрудники' недоступна.\n"
                "Можете перейти на вкладку 'Анализ' для запуска."
            )
        
        # Логируем
        self._log("✓ Настройки применены")
        self._log(f"  - Файлов логов: {len(self.logs_paths)}")
        if mapping_file and mapping_file.strip():
            self._log(f"  - Файл маппинга: {mapping_file}")
    
    def _start_analysis(self):
        """Запуск анализа в отдельном потоке"""
        if self.is_running:
            messagebox.showwarning(
                "Внимание",
                "Анализ уже выполняется!"
            )
            return
        
        # Проверка файлов
        if not self.logs_paths or len(self.logs_paths) == 0:
            messagebox.showerror(
                "Ошибка",
                "Не выбрано ни одного файла логов!"
            )
            return
        
        # Проверяем существование всех файлов
        missing_files = [
            p for p in self.logs_paths if not os.path.exists(p)
        ]
        if missing_files:
            messagebox.showerror(
                "Ошибка",
                f"Не найдены файлы:\n" +
                "\n".join(os.path.basename(f) for f in missing_files)
            )
            return
        
        # Профили теперь необязательны
        prefs_path = self.prefs_path.get()
        if prefs_path and not os.path.exists(prefs_path):
            result = messagebox.askyesno(
                "Внимание",
                "Файл профилей не найден!\n\n"
                "Продолжить без профилей?\n"
                "Будут использованы дефолтные настройки для всех сотрудников."
            )
            if not result:
                return
            # Очищаем путь, чтобы использовать дефолты
            self.prefs_path.set("")
        
        # Запуск в потоке
        self.is_running = True
        self.notebook.select(self.analysis_tab)
        self._clear_log()
        self.progress.start()
        self._set_status("⏳ Выполняется анализ...")
        
        thread = threading.Thread(target=self._run_analysis, daemon=True)
        thread.start()
    
    def _run_analysis(self):
        """Основная логика анализа"""
        try:
            self._log("="*60)
            self._log("LogStorm - Запуск анализа")
            self._log(f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self._log("="*60 + "\n")
            
            # 1. Загрузка данных
            self._log("[1/5] 📂 Загрузка данных...")
            
            # Загрузка PersonMapper для NDJSON (опционально)
            person_mapper = None
            mapping_path = self.mapping_path.get()
            if mapping_path and os.path.exists(mapping_path):
                try:
                    person_mapper = PersonMapper(mapping_path)
                    self._log(f"✅ Загружен маппинг: {mapping_path}")
                    self._log(f"   Сотрудников: {len(person_mapper.mappings)}")
                    self._log(f"   Алиасов: {len(person_mapper.aliases)}")
                except Exception as e:
                    self._log(f"⚠️ Ошибка загрузки маппинга: {e}")
                    person_mapper = None
            
            # Передаём список файлов или одиночный файл
            if len(self.logs_paths) == 1:
                self._log(f"Файл: {os.path.basename(self.logs_paths[0])}")
                df = DataLoader.load_logs(
                    self.logs_paths[0],
                    file_type=self.file_type.get(),
                    person_mapper=person_mapper
                )
            else:
                self._log(f"Файлов: {len(self.logs_paths)}")
                df = DataLoader.load_logs(
                    self.logs_paths,
                    file_type=self.file_type.get(),
                    person_mapper=person_mapper
                )
            
            # Загрузка профилей (опционально)
            prefs_path = self.prefs_path.get()
            if prefs_path and os.path.exists(prefs_path):
                prefs = DataLoader.load_preferences(prefs_path)
            else:
                # Если есть маппер, конвертируем его в формат prefs
                if person_mapper:
                    prefs = person_mapper.convert_to_prefs_format()
                    self._log("✅ Расписания загружены из маппинга")
                else:
                    prefs = {}
                    self._log("⚠️ Профили не используются - дефолтные настройки")
            
            self._log(
                f"✅ Загружено {len(df)} записей, "
                f"{len(prefs)} профилей\n"
            )
            
            df = DataLoader.filter_known_users(df, prefs)
            
            # 2. Анализ
            self._log("\n[2/5] 🔍 Анализ посещаемости...")
            service = AttendanceService(df, prefs)
            self.records = service.analyze_all()
            self._log(f"✅ Проанализировано {len(self.records)} записей\n")
            
            # 3. Сводка
            self._log("\n[3/5] 📊 Генерация сводки...")
            summary = SummaryReporter(self.records)
            summary.print_summary()
            self._log("✅ Сводка готова\n")
            
            # 4. Excel
            self._log("\n[4/5] 📝 Создание Excel отчёта...")
            os.makedirs(os.path.dirname(self.output_path.get()) or '.',
                       exist_ok=True)
            excel_reporter = ExcelReporter(self.records)
            success = excel_reporter.generate_report(self.output_path.get())
            
            if success:
                formatter = ExcelFormatter(
                    self.output_path.get(),
                    excel_reporter
                )
                formatter.format_all()
                self._log(f"✅ Отчёт сохранён: {self.output_path.get()}\n")
            else:
                self._log("❌ Ошибка создания отчёта\n")
            
            # 5. AI
            if self.enable_ai.get():
                self._log("\n[5/5] 🤖 AI анализ...")
                try:
                    ai = AIService(self.records)
                    ai.generate_summary()
                    self._log("✅ AI анализ завершён\n")
                except Exception as e:
                    self._log(f"⚠️ AI анализ недоступен: {e}\n")
            else:
                self._log("\n[5/5] 🤖 AI анализ отключен\n")
            
            self._log("\n" + "="*60)
            self._log("✅ АНАЛИЗ ЗАВЕРШЁН УСПЕШНО!")
            self._log("="*60)
            
            self.root.after(0, lambda: self._set_status("✅ Анализ завершён"))
            self.root.after(
                0,
                lambda: messagebox.showinfo(
                    "Готово",
                    f"Анализ завершён!\n\nОтчёт: {self.output_path.get()}"
                )
            )
            
        except Exception as e:
            error_msg = f"❌ ОШИБКА: {str(e)}"
            self._log(f"\n{error_msg}")
            self.root.after(0, lambda: self._set_status("❌ Ошибка"))
            self.root.after(
                0,
                lambda: messagebox.showerror("Ошибка", str(e))
            )
        
        finally:
            self.is_running = False
            self.root.after(0, self.progress.stop)
    
    def _open_report(self):
        """Открыть отчёт"""
        if os.path.exists(self.output_path.get()):
            os.startfile(self.output_path.get())
        else:
            messagebox.showwarning(
                "Внимание",
                "Отчёт ещё не создан!"
            )
    
    def _clear_log(self):
        """Очистить лог"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def _log(self, message: str):
        """Добавить сообщение в лог"""
        def _append():
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
        
        if threading.current_thread() == threading.main_thread():
            _append()
        else:
            self.root.after(0, _append)
    
    def _set_status(self, text: str):
        """Установить статус"""
        self.status_label.config(text=text)


def main():
    """Точка входа"""
    root = tk.Tk()
    app = LogStormGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
