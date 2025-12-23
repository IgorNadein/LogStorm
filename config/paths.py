"""
Paths Configuration - пути к файлам
"""

from dataclasses import dataclass


@dataclass
class PathsConfig:
    """Настройки путей к файлам"""
    
    logs_file: str = 'logs/attendance.csv'
    person_mapping_file: str = 'person_mapping.json'
    output_excel_file: str = 'attendance_report.xlsx'


# Глобальный экземпляр
paths_config = PathsConfig()
