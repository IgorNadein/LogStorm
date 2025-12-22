"""
Formatting Configuration - настройки форматирования Excel отчётов
"""

from dataclasses import dataclass


@dataclass
class FormattingConfig:
    """Настройки форматирования Excel"""
    
    # Цвета заголовков
    header_color: str = "4472C4"  # Синий
    summary_header_color: str = "9966CC"  # Фиолетовый
    
    # Цвета фона строк (светлые)
    late_bg_color: str = "FFE699"  # Светло-желтый (опоздания)
    overtime_bg_color: str = "C6EFCE"  # Светло-зеленый (переработки)
    suspicious_bg_color: str = "FFB3B3"  # Светло-красный
    
    # Цвета ячеек (яркие)
    late_cell_color: str = "FFA500"  # Оранжевый (опоздание)
    underwork_cell_color: str = "FFFF00"  # Желтый (недоработка)
    overtime_cell_color: str = "00B050"  # Зеленый (переработка)
    suspicious_cell_color: str = "8B0000"  # Темно-красный
    technical_fill_color: str = "FF0000"  # Красный (тех. сбой)
    
    # Названия листов Excel
    sheet_main_report: str = 'Отчет по дням'
    sheet_suspicious: str = 'Подозрительные случаи'
    sheet_month_prefix: str = 'Месяц '


# Глобальный экземпляр
formatting_config = FormattingConfig()
