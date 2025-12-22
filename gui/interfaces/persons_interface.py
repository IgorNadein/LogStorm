"""
Persons Interface - интерфейс управления сотрудниками
"""

from typing import Dict, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QHeaderView
)
from qfluentwidgets import (
    CardWidget, PrimaryPushButton, PushButton,
    StrongBodyLabel, BodyLabel
)


class PersonsInterface(QWidget):
    """Интерфейс управления сотрудниками"""
    
    def __init__(self, parent=None):
        """
        Инициализация интерфейса
        
        Args:
            parent: Родительский виджет
        """
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
        
        info_label = BodyLabel(
            "Список сотрудников с настройками и алиасами"
        )
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
        self.persons_table = QTableWidget(self)
        self.persons_table.setColumnCount(5)
        self.persons_table.setHorizontalHeaderLabels([
            "ID", "Имя", "Время начала", "Рабочие дни", "Алиасы"
        ])
        
        # Настройки таблицы
        header = self.persons_table.horizontalHeader()
        header.setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        header.setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        header.setSectionResizeMode(
            4, QHeaderView.ResizeMode.ResizeToContents
        )
        
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
        """
        Обновить таблицу сотрудников
        
        Args:
            prefs: Словарь настроек сотрудников
            aliases: Словарь алиасов
        """
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
            aliases_str = (
                ', '.join(person_aliases) if person_aliases else '-'
            )
            self.persons_table.setItem(
                row, 4, QTableWidgetItem(aliases_str)
            )
            
            row += 1
        
        self.persons_table.setSortingEnabled(True)
    
    def get_selected_person_id(self) -> Optional[str]:
        """
        Получить ID выбранного сотрудника
        
        Returns:
            ID сотрудника или None если ничего не выбрано
        """
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
