"""
LogStorm Application Bootstrap - инициализация контейнера зависимостей

Этот модуль настраивает все сервисы приложения и их зависимости.
"""

from di_container import ServiceContainer, get_container, set_container
from config import config_manager, ConfigManager


def create_app_container() -> ServiceContainer:
    """
    Создаёт и настраивает контейнер зависимостей для приложения.
    
    Returns:
        Настроенный ServiceContainer
    """
    container = ServiceContainer()
    
    # === Конфигурация ===
    container.register_singleton(
        ConfigManager,
        instance=config_manager
    )
    
    # === Сервисы данных ===
    # Ленивая загрузка для избежания циклических импортов
    def create_data_loader(c: ServiceContainer):
        from services.data_loader import DataLoader
        return DataLoader()
    
    def create_attendance_service(c: ServiceContainer):
        from services.attendance_service import AttendanceService
        return AttendanceService()
    
    def create_logscam_loader(c: ServiceContainer):
        from services.logscam_loader import LogsCamLoader
        return LogsCamLoader()
    
    def create_ai_service(c: ServiceContainer):
        from services.ai_service import AIService
        return AIService()
    
    container.register_singleton('DataLoader', create_data_loader)
    container.register_singleton('AttendanceService', create_attendance_service)
    container.register_singleton('LogsCamLoader', create_logscam_loader)
    container.register_singleton('AIService', create_ai_service)
    
    # === Анализаторы ===
    def create_status_analyzer(c: ServiceContainer):
        from analyzers.status_analyzer import StatusAnalyzer
        return StatusAnalyzer()
    
    def create_technical_analyzer(c: ServiceContainer):
        from analyzers.technical_analyzer import TechnicalAnalyzer
        return TechnicalAnalyzer()
    
    container.register_factory('StatusAnalyzer', create_status_analyzer)
    container.register_factory('TechnicalAnalyzer', create_technical_analyzer)
    
    # === Репортеры ===
    def create_excel_reporter(c: ServiceContainer):
        from reporters.excel_reporter import ExcelReporter
        return ExcelReporter()
    
    def create_summary_reporter(c: ServiceContainer):
        from reporters.summary_reporter import SummaryReporter
        return SummaryReporter()
    
    container.register_factory('ExcelReporter', create_excel_reporter)
    container.register_factory('SummaryReporter', create_summary_reporter)
    
    # === Валидаторы ===
    def create_absence_validator(c: ServiceContainer):
        from validators.absence_validator import AbsenceValidator
        return AbsenceValidator()
    
    def create_time_validator(c: ServiceContainer):
        from validators.time_validator import TimeValidator
        return TimeValidator()
    
    container.register_factory('AbsenceValidator', create_absence_validator)
    container.register_factory('TimeValidator', create_time_validator)
    
    return container


def bootstrap_app() -> ServiceContainer:
    """
    Инициализирует приложение и возвращает контейнер.
    
    Использование:
        from app_bootstrap import bootstrap_app
        
        container = bootstrap_app()
        loader = container.get('DataLoader')
    """
    container = create_app_container()
    set_container(container)
    return container


# Автоинициализация при импорте (опционально)
# bootstrap_app()
