"""
Localization Configuration - локализация (названия дней, месяцев)
"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class LocalizationConfig:
    """Настройки локализации"""
    
    days_ru: Dict[str, str] = field(default_factory=lambda: {
        'Monday': 'Понедельник',
        'Tuesday': 'Вторник',
        'Wednesday': 'Среда',
        'Thursday': 'Четверг',
        'Friday': 'Пятница',
        'Saturday': 'Суббота',
        'Sunday': 'Воскресенье'
    })
    
    days_order: List[str] = field(default_factory=lambda: [
        'Monday', 'Tuesday', 'Wednesday', 'Thursday',
        'Friday', 'Saturday', 'Sunday'
    ])
    
    months_ru: Dict[int, str] = field(default_factory=lambda: {
        1: 'Январь',
        2: 'Февраль',
        3: 'Март',
        4: 'Апрель',
        5: 'Май',
        6: 'Июнь',
        7: 'Июль',
        8: 'Август',
        9: 'Сентябрь',
        10: 'Октябрь',
        11: 'Ноябрь',
        12: 'Декабрь'
    })


# Глобальный экземпляр
localization_config = LocalizationConfig()
