"""
Analysis Interface - интерфейс анализа логов с фильтрами
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QHeaderView,
    QTableWidgetItem, QAbstractItemView
)
from PySide6.QtCore import Qt, QTimer
from qfluentwidgets import (
    CardWidget, PrimaryPushButton, PushButton, TableWidget,
    StrongBodyLabel, BodyLabel, IndeterminateProgressBar,
    ComboBox, CalendarPicker, SearchLineEdit, FluentIcon
)
from datetime import datetime


class AnalysisInterface(QWidget):
    """Интерфейс анализа логов посещений с фильтрами"""
    
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("analysisInterface")
        self._all_results = []  # Все результаты для фильтрации
        self._current_filtered = []  # Текущие отфильтрованные результаты
        
        # Таймер для debouncing поиска
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(300)  # 300 мс задержка
        self._search_timer.timeout.connect(self._apply_filters)
        
        # Таймер для ленивой загрузки таблицы
        self._populate_timer = QTimer(self)
        self._populate_timer.setSingleShot(False)
        self._populate_timer.setInterval(0)  # Как можно быстрее
        self._populate_timer.timeout.connect(self._populate_batch)
        self._populate_index = 0
        self._populate_data = []
        
        # Настройки производительности
        self.MAX_DISPLAY_ROWS = 2000  # Максимум записей в таблице
        self.BATCH_SIZE = 100  # Размер батча для ленивой загрузки
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)
        
        title = StrongBodyLabel("Анализ логов", self)
        layout.addWidget(title)
        
        # === Карточка управления ===
        control_card = CardWidget(self)
        control_layout = QVBoxLayout(control_card)
        control_layout.setSpacing(12)
        
        self.status_label = BodyLabel("Готов к анализу")
        control_layout.addWidget(self.status_label)
        
        # Прогресс бар (индикатор + процент)
        self.progress_bar = IndeterminateProgressBar(self)
        self.progress_bar.setVisible(False)
        control_layout.addWidget(self.progress_bar)
        
        # Прогресс с процентами (показывается при детальном прогрессе)
        from qfluentwidgets import ProgressBar
        self.detail_progress = ProgressBar(self)
        self.detail_progress.setVisible(False)
        control_layout.addWidget(self.detail_progress)
        
        # Кнопки в ряд
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)
        
        self.run_btn = PrimaryPushButton(
            FluentIcon.PLAY, "Запустить анализ", self
        )
        self.run_btn.setMinimumHeight(36)
        buttons_layout.addWidget(self.run_btn)
        
        self.export_btn = PushButton(
            FluentIcon.DOWNLOAD, "Экспорт в Excel", self
        )
        self.export_btn.setMinimumHeight(36)
        self.export_btn.setEnabled(False)
        buttons_layout.addWidget(self.export_btn)
        
        buttons_layout.addStretch()
        control_layout.addLayout(buttons_layout)
        
        layout.addWidget(control_card)
        
        # === Карточка фильтров ===
        filter_card = CardWidget(self)
        filter_layout = QVBoxLayout(filter_card)
        filter_layout.setSpacing(12)
        
        filter_title = StrongBodyLabel("Фильтры")
        filter_layout.addWidget(filter_title)
        
        # Первый ряд фильтров
        row1 = QHBoxLayout()
        row1.setSpacing(16)
        
        # Фильтр по сотруднику
        employee_label = BodyLabel("Сотрудник:")
        row1.addWidget(employee_label)
        self.employee_filter = ComboBox(self)
        self.employee_filter.setMinimumWidth(180)
        self.employee_filter.addItem("Все")
        self.employee_filter.currentTextChanged.connect(self._apply_filters)
        row1.addWidget(self.employee_filter)
        
        row1.addSpacing(20)
        
        # Фильтр по периоду
        period_label = BodyLabel("С:")
        row1.addWidget(period_label)
        self.date_from = CalendarPicker(self)
        self.date_from.dateChanged.connect(self._apply_filters)
        row1.addWidget(self.date_from)
        
        period_to_label = BodyLabel("По:")
        row1.addWidget(period_to_label)
        self.date_to = CalendarPicker(self)
        self.date_to.dateChanged.connect(self._apply_filters)
        row1.addWidget(self.date_to)
        
        row1.addStretch()
        filter_layout.addLayout(row1)
        
        # Второй ряд фильтров
        row2 = QHBoxLayout()
        row2.setSpacing(16)
        
        # Фильтр по статусу
        status_label = BodyLabel("Статус:")
        row2.addWidget(status_label)
        self.status_filter = ComboBox(self)
        self.status_filter.setMinimumWidth(180)
        self.status_filter.addItems([
            "Все", "Опоздания", "Ранние уходы", "Переработки",
            "Технические сбои", "Отсутствия"
        ])
        self.status_filter.currentTextChanged.connect(self._apply_filters)
        row2.addWidget(self.status_filter)
        
        row2.addSpacing(20)
        
        # Поиск с debouncing
        self.search_edit = SearchLineEdit(self)
        self.search_edit.setPlaceholderText("Поиск...")
        self.search_edit.setMinimumWidth(200)
        self.search_edit.textChanged.connect(self._on_search_changed)
        row2.addWidget(self.search_edit)
        
        # Кнопка сброса
        self.reset_btn = PushButton("Сбросить", self)
        self.reset_btn.clicked.connect(self._reset_filters)
        row2.addWidget(self.reset_btn)
        
        row2.addStretch()
        filter_layout.addLayout(row2)
        
        layout.addWidget(filter_card)
        
        # === Карточка результатов ===
        results_card = CardWidget(self)
        results_layout = QVBoxLayout(results_card)
        results_layout.setSpacing(12)
        
        # Заголовок с счётчиком
        results_header = QHBoxLayout()
        results_label = StrongBodyLabel("Результаты анализа")
        results_header.addWidget(results_label)
        
        self.count_label = BodyLabel("")
        results_header.addWidget(self.count_label)
        results_header.addStretch()
        results_layout.addLayout(results_header)
        
        # Таблица результатов
        self.results_table = TableWidget(self)
        self.results_table.setColumnCount(9)
        self.results_table.setHorizontalHeaderLabels([
            "Дата", "День", "Сотрудник", "Приход", "Уход",
            "Часов", "Опоздание", "Ранний уход", "Статус"
        ])
        self.results_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.results_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        
        # Оптимизация производительности таблицы
        self.results_table.setAlternatingRowColors(True)
        # Используем фиксированные размеры колонок для производительности
        header = self.results_table.horizontalHeader()
        header.setDefaultSectionSize(100)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        # Последняя колонка растягивается
        header.setStretchLastSection(True)
        
        results_layout.addWidget(self.results_table)
        
        layout.addWidget(results_card, 1)  # Растягиваем
    
    def set_analyzing(self, analyzing: bool):
        """Установить состояние анализа"""
        self.run_btn.setEnabled(not analyzing)
        self.progress_bar.setVisible(analyzing)
        self.detail_progress.setVisible(False)  # Скрываем детальный прогресс
        if analyzing:
            self.progress_bar.start()
            self.status_label.setText("Выполняется анализ...")
        else:
            self.progress_bar.stop()
    
    def set_progress(self, current: int, total: int, message: str = ""):
        """
        Установить детальный прогресс анализа
        
        Args:
            current: Текущий шаг
            total: Всего шагов
            message: Дополнительное сообщение
        """
        # Скрываем индикатор и показываем детальный прогресс
        self.progress_bar.setVisible(False)
        self.detail_progress.setVisible(True)
        
        # Обновляем прогресс
        percent = int((current / total) * 100) if total > 0 else 0
        self.detail_progress.setValue(percent)
        
        # Обновляем текст статуса
        if message:
            self.status_label.setText(f"{message} ({percent}%)")
        else:
            self.status_label.setText(
                f"Анализ: {current}/{total} ({percent}%)"
            )
    
    def set_results(self, records: list):
        """
        Установить результаты анализа
        
        Args:
            records: Список AttendanceRecord
        """
        self._all_results = records
        
        # Обновляем список сотрудников в фильтре
        self.employee_filter.clear()
        self.employee_filter.addItem("Все")
        employees = sorted(set(r.display_name for r in records))
        self.employee_filter.addItems(employees)
        
        # Устанавливаем диапазон дат
        if records:
            dates = [r.date for r in records]
            min_date = min(dates)
            max_date = max(dates)
            from PySide6.QtCore import QDate
            self.date_from.setDate(
                QDate(min_date.year, min_date.month, min_date.day)
            )
            self.date_to.setDate(
                QDate(max_date.year, max_date.month, max_date.day)
            )
        
        # Включаем кнопку экспорта
        self.export_btn.setEnabled(len(records) > 0)
        
        # Применяем фильтры и отображаем
        self._apply_filters()
        
        self.status_label.setText(
            f"Анализ завершён. Найдено записей: {len(records)}"
        )
    
    def _on_search_changed(self):
        """Обработка изменения поискового запроса с debouncing"""
        # Останавливаем предыдущий таймер
        self._search_timer.stop()
        # Останавливаем загрузку таблицы если идёт
        self._populate_timer.stop()
        # Запускаем новый таймер (сработает через 300 мс)
        self._search_timer.start()
    
    def _apply_filters(self):
        """Применить фильтры к результатам"""
        if not self._all_results:
            return
        
        filtered = self._all_results.copy()
        
        # Фильтр по сотруднику
        employee = self.employee_filter.currentText()
        if employee and employee != "Все":
            filtered = [r for r in filtered if r.display_name == employee]
        
        # Фильтр по дате
        date_from = self.date_from.date
        date_to = self.date_to.date
        if date_from and date_to:
            from datetime import date as dt_date
            from_date = dt_date(
                date_from.year(), date_from.month(), date_from.day()
            )
            to_date = dt_date(
                date_to.year(), date_to.month(), date_to.day()
            )
            filtered = [
                r for r in filtered
                if from_date <= r.date <= to_date
            ]
        
        # Фильтр по статусу
        status = self.status_filter.currentText()
        if status == "Опоздания":
            filtered = [r for r in filtered if r.is_late]
        elif status == "Ранние уходы":
            filtered = [r for r in filtered if r.is_early_leave]
        elif status == "Переработки":
            filtered = [r for r in filtered if r.is_overtime]
        elif status == "Технические сбои":
            filtered = [r for r in filtered if r.has_technical_issues]
        elif status == "Отсутствия":
            filtered = [
                r for r in filtered
                if r.is_workday and r.appearances == 0
            ]
        
        # Поиск по тексту
        search_text = self.search_edit.text().strip().lower()
        if search_text:
            filtered = [
                r for r in filtered
                if search_text in r.display_name.lower()
                or search_text in str(r.date)
            ]
        
        # Сохраняем отфильтрованные результаты
        self._current_filtered = filtered
        
        # Проверяем, нужно ли ограничить вывод
        display_count = len(filtered)
        is_limited = False
        if display_count > self.MAX_DISPLAY_ROWS:
            display_count = self.MAX_DISPLAY_ROWS
            is_limited = True
        
        # Обновляем счётчик с предупреждением
        if is_limited:
            self.count_label.setText(
                f"⚠️ Показано первых {display_count} из {len(filtered)} "
                f"(всего {len(self._all_results)})"
            )
        else:
            self.count_label.setText(
                f"(показано {len(filtered)} из {len(self._all_results)})"
            )
        
        # Запускаем ленивую загрузку таблицы
        self._start_lazy_populate(filtered[:display_count])
    
    def _start_lazy_populate(self, records: list):
        """Запустить ленивую загрузку таблицы батчами"""
        # Останавливаем предыдущую загрузку если была
        self._populate_timer.stop()
        
        # Очищаем таблицу
        self.results_table.setUpdatesEnabled(False)
        self.results_table.setSortingEnabled(False)
        self.results_table.setRowCount(0)
        self.results_table.setUpdatesEnabled(True)
        
        # Если записей мало, загружаем сразу
        if len(records) <= self.BATCH_SIZE:
            self._populate_table_sync(records)
            return
        
        # Иначе запускаем ленивую загрузку
        self._populate_data = records
        self._populate_index = 0
        
        # Резервируем строки сразу
        self.results_table.setRowCount(len(records))
        
        # Запускаем таймер
        self._populate_timer.start()
    
    def _populate_batch(self):
        """Загрузить следующий батч записей"""
        if self._populate_index >= len(self._populate_data):
            # Загрузка завершена
            self._populate_timer.stop()
            self.results_table.setSortingEnabled(True)
            return
        
        # Определяем диапазон батча
        start = self._populate_index
        end = min(start + self.BATCH_SIZE, len(self._populate_data))
        
        from config import DAYS_RU
        
        # Отключаем обновления для батча
        self.results_table.setUpdatesEnabled(False)
        
        # Заполняем батч
        for i in range(start, end):
            record = self._populate_data[i]
            row = i
            
            # Дата
            self.results_table.setItem(
                row, 0, QTableWidgetItem(str(record.date))
            )
            # День недели
            day_ru = DAYS_RU.get(record.weekday, record.weekday)
            self.results_table.setItem(row, 1, QTableWidgetItem(day_ru))
            # Сотрудник
            self.results_table.setItem(
                row, 2, QTableWidgetItem(record.display_name)
            )
            # Приход
            arrival = (
                record.arrival_time.strftime('%H:%M')
                if record.arrival_time else '-'
            )
            self.results_table.setItem(row, 3, QTableWidgetItem(arrival))
            # Уход
            departure = (
                record.departure_time.strftime('%H:%M')
                if record.departure_time else '-'
            )
            self.results_table.setItem(row, 4, QTableWidgetItem(departure))
            # Часов
            self.results_table.setItem(
                row, 5, QTableWidgetItem(f"{record.work_hours:.1f}")
            )
            # Опоздание
            late = f"{record.late_minutes} мин" if record.is_late else "-"
            self.results_table.setItem(row, 6, QTableWidgetItem(late))
            # Ранний уход
            early = (
                f"{record.early_leave_minutes} мин"
                if record.is_early_leave else "-"
            )
            self.results_table.setItem(row, 7, QTableWidgetItem(early))
            # Статус
            status = self._get_status_text(record)
            self.results_table.setItem(row, 8, QTableWidgetItem(status))
        
        # Включаем обновления
        self.results_table.setUpdatesEnabled(True)
        
        # Обновляем индекс
        self._populate_index = end
    
    def _populate_table_sync(self, records: list):
        """Синхронная загрузка для малого количества записей"""
        self.results_table.setUpdatesEnabled(False)
        self.results_table.setSortingEnabled(False)
        self.results_table.setRowCount(len(records))
        
        from config import DAYS_RU
        
        for row, record in enumerate(records):
            # Дата
            self.results_table.setItem(
                row, 0, QTableWidgetItem(str(record.date))
            )
            # День недели
            day_ru = DAYS_RU.get(record.weekday, record.weekday)
            self.results_table.setItem(row, 1, QTableWidgetItem(day_ru))
            # Сотрудник
            self.results_table.setItem(
                row, 2, QTableWidgetItem(record.display_name)
            )
            # Приход
            arrival = (
                record.arrival_time.strftime('%H:%M')
                if record.arrival_time else '-'
            )
            self.results_table.setItem(row, 3, QTableWidgetItem(arrival))
            # Уход
            departure = (
                record.departure_time.strftime('%H:%M')
                if record.departure_time else '-'
            )
            self.results_table.setItem(row, 4, QTableWidgetItem(departure))
            # Часов
            self.results_table.setItem(
                row, 5, QTableWidgetItem(f"{record.work_hours:.1f}")
            )
            # Опоздание
            late = f"{record.late_minutes} мин" if record.is_late else "-"
            self.results_table.setItem(row, 6, QTableWidgetItem(late))
            # Ранний уход
            early = (
                f"{record.early_leave_minutes} мин"
                if record.is_early_leave else "-"
            )
            self.results_table.setItem(row, 7, QTableWidgetItem(early))
            # Статус
            status = self._get_status_text(record)
            self.results_table.setItem(row, 8, QTableWidgetItem(status))
        
        # Включаем обновление и сортировку
        self.results_table.setSortingEnabled(True)
        self.results_table.setUpdatesEnabled(True)
    
    def _get_status_text(self, record) -> str:
        """Получить текст статуса записи"""
        statuses = []
        if record.has_technical_issues:
            statuses.append("⚠️ Тех.сбой")
        if record.is_workday and record.appearances == 0:
            statuses.append("❌ Отсутствие")
        if record.is_overtime:
            statuses.append("⏰ Переработка")
        if not statuses:
            if record.is_workday:
                statuses.append("✅ Норма")
            else:
                statuses.append("🔵 Выходной")
        return " | ".join(statuses)
    
    def _reset_filters(self):
        """Сбросить все фильтры"""
        self.employee_filter.setCurrentIndex(0)
        self.status_filter.setCurrentIndex(0)
        self.search_edit.clear()
        
        # Сбрасываем даты к исходному диапазону
        if self._all_results:
            dates = [r.date for r in self._all_results]
            min_date = min(dates)
            max_date = max(dates)
            from PySide6.QtCore import QDate
            self.date_from.setDate(
                QDate(min_date.year, min_date.month, min_date.day)
            )
            self.date_to.setDate(
                QDate(max_date.year, max_date.month, max_date.day)
            )
