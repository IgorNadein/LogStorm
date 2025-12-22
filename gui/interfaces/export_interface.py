"""
Export Interface - интерфейс экспорта данных
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout
from qfluentwidgets import (
    CardWidget, PrimaryPushButton, CheckBox,
    StrongBodyLabel, BodyLabel
)


class ExportInterface(QWidget):
    """Интерфейс экспорта результатов"""
    
    def __init__(self, parent=None):
        """
        Инициализация интерфейса
        
        Args:
            parent: Родительский виджет
        """
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
        
        info_label = BodyLabel(
            "Экспорт результатов анализа в различные форматы"
        )
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
