"""
Analysis Interface - интерфейс анализа логов с фильтрами
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QHeaderView,
    QTableWidgetItem, QAbstractItemView
)
from PySide6.QtCore import Qt
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
        
        # Прогресс бар
        self.progress_bar = IndeterminateProgressBar(self)
        self.progress_bar.setVisible(False)
        control_layout.addWidget(self.progress_bar)
        
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
        
        # Поиск
        self.search_edit = SearchLineEdit(self)
        self.search_edit.setPlaceholderText("Поиск...")
        self.search_edit.setMinimumWidth(200)
        self.search_edit.textChanged.connect(self._apply_filters)
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
        self.results_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.results_table.horizontalHeader().setStretchLastSection(True)
        results_layout.addWidget(self.results_table)
        
        layout.addWidget(results_card, 1)  # Растягиваем
    
    def set_analyzing(self, analyzing: bool):
        """Установить состояние анализа"""
        self.run_btn.setEnabled(not analyzing)
        self.progress_bar.setVisible(analyzing)
        if analyzing:
            self.progress_bar.start()
            self.status_label.setText("Выполняется анализ...")
        else:
            self.progress_bar.stop()
    
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
        
        # Обновляем таблицу
        self._populate_table(filtered)
        
        # Обновляем счётчик
        self.count_label.setText(
            f"(показано {len(filtered)} из {len(self._all_results)})"
        )
    
    def _populate_table(self, records: list):
        """Заполнить таблицу записями"""
        self.results_table.setRowCount(len(records))
        
        for row, record in enumerate(records):
            # Дата
            self.results_table.setItem(
                row, 0, QTableWidgetItem(str(record.date))
            )
            # День недели
            from config import DAYS_RU
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
