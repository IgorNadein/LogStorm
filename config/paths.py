"""
Paths Configuration - пути к файлам
"""

from dataclasses import dataclass


@dataclass
class PathsConfig:
    """Настройки путей к файлам"""
    
    logs_file: str = 'data/attendance.csv'
    person_mapping_file: str = ''
    output_excel_file: str = 'reports/attendance_report.xlsx'


# Глобальный экземпляр
paths_config = PathsConfig()
