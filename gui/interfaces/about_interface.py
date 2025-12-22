"""
About Interface - интерфейс О программе
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout
from qfluentwidgets import CardWidget, StrongBodyLabel, BodyLabel


class AboutInterface(QWidget):
    """Интерфейс О программе"""
    
    def __init__(self, parent=None):
        """
        Инициализация интерфейса
        
        Args:
            parent: Родительский виджет
        """
        super().__init__(parent=parent)
        self.setObjectName("aboutInterface")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)
        
        title = StrongBodyLabel("О программе", self)
        layout.addWidget(title)
        
        # Карточка с информацией
        card = CardWidget(self)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(16)
        
        app_name = StrongBodyLabel("LogStorm")
        card_layout.addWidget(app_name)
        
        version_label = BodyLabel("Версия 2.7")
        card_layout.addWidget(version_label)
        
        desc_label = BodyLabel(
            "Система анализа логов посещений с использованием AI\n\n"
            "Функции:\n"
            "• Анализ логов посещений сотрудников\n"
            "• Интеллектуальное определение причин отсутствия\n"
            "• Управление графиками работы\n"
            "• Экспорт отчётов в Excel"
        )
        card_layout.addWidget(desc_label)
        
        layout.addWidget(card)
        layout.addStretch()
