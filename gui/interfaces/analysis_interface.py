"""
Analysis Interface - интерфейс анализа логов
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout
from qfluentwidgets import (
    CardWidget, PrimaryPushButton, ListWidget,
    StrongBodyLabel, BodyLabel, IndeterminateProgressBar
)


class AnalysisInterface(QWidget):
    """Интерфейс анализа логов посещений"""
    
    def __init__(self, parent=None):
        """
        Инициализация интерфейса
        
        Args:
            parent: Родительский виджет
        """
        super().__init__(parent=parent)
        self.setObjectName("analysisInterface")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)
        
        title = StrongBodyLabel("Анализ логов", self)
        layout.addWidget(title)
        
        # Карточка статуса
        status_card = CardWidget(self)
        status_layout = QVBoxLayout(status_card)
        status_layout.setSpacing(12)
        
        self.status_label = BodyLabel("Готов к анализу")
        status_layout.addWidget(self.status_label)
        
        # Прогресс бар
        self.progress_bar = IndeterminateProgressBar(self)
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.progress_bar)
        
        # Кнопка запуска
        self.run_btn = PrimaryPushButton("Запустить анализ", self)
        self.run_btn.setMinimumHeight(36)
        status_layout.addWidget(self.run_btn)
        
        layout.addWidget(status_card)
        
        # Карточка результатов
        results_card = CardWidget(self)
        results_layout = QVBoxLayout(results_card)
        results_layout.setSpacing(12)
        
        results_label = StrongBodyLabel("Результаты анализа")
        results_layout.addWidget(results_label)
        
        self.results_list = ListWidget(self)
        results_layout.addWidget(self.results_list)
        
        layout.addWidget(results_card)
        layout.addStretch()
    
    def set_analyzing(self, analyzing: bool):
        """
        Установить состояние анализа
        
        Args:
            analyzing: True если анализ выполняется
        """
        self.run_btn.setEnabled(not analyzing)
        self.progress_bar.setVisible(analyzing)
        if analyzing:
            self.progress_bar.start()
        else:
            self.progress_bar.stop()
