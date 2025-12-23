"""
Interfaces package - страницы интерфейса приложения
"""

from .settings_interface import SettingsInterface
from .persons_interface import PersonsInterface
from .logs_interface import LogsInterface
from .analysis_interface import AnalysisInterface
from .about_interface import AboutInterface

__all__ = [
    'SettingsInterface',
    'PersonsInterface',
    'LogsInterface',
    'AnalysisInterface',
    'AboutInterface'
]
