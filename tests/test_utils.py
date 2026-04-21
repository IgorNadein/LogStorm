"""
Тесты для модуля логирования и исключений
(utils/logging.py, utils/exceptions.py)
"""

import sys
import os
import logging

# Добавляем корневой каталог в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from utils.logging import setup_logging, get_logger, init_logging  # noqa: E402
from utils.exceptions import (  # noqa: E402
    LogStormError,
    ConfigError,
    ConfigFileNotFoundError,
    ConfigValidationError,
    DataError,
    FileFormatError,
    EmptyDataError,
    AnalysisError,
    PersonNotFoundError,
    ScheduleError,
    ExportError,
    ExcelExportError,
    FileLockedError,
    DeviceError,
    DeviceConnectionError,
    DeviceAuthError
)


class TestExceptions:
    """Тесты пользовательских исключений"""
    
    def test_base_exception(self):
        """Тест базового исключения"""
        error = LogStormError("Тестовая ошибка", "Детали ошибки")
        assert error.message == "Тестовая ошибка"
        assert error.details == "Детали ошибки"
        assert "Тестовая ошибка" in str(error)
        assert "Детали" in str(error)
    
    def test_base_exception_without_details(self):
        """Тест базового исключения без деталей"""
        error = LogStormError("Простая ошибка")
        assert error.details is None
        assert str(error) == "Простая ошибка"
    
    def test_config_file_not_found(self):
        """Тест ошибки отсутствующего конфига"""
        error = ConfigFileNotFoundError("/path/to/config.json")
        assert error.file_path == "/path/to/config.json"
        assert "не найден" in str(error)
    
    def test_file_format_error(self):
        """Тест ошибки формата файла"""
        error = FileFormatError("data.txt", "CSV")
        assert error.file_path == "data.txt"
        assert error.expected_format == "CSV"
        assert "CSV" in str(error)
    
    def test_person_not_found(self):
        """Тест ошибки ненайденного сотрудника"""
        error = PersonNotFoundError("ivan_ivanov")
        assert error.person_id == "ivan_ivanov"
        assert "ivan_ivanov" in str(error)
    
    def test_file_locked_error(self):
        """Тест ошибки заблокированного файла"""
        error = FileLockedError("report.xlsx")
        assert error.file_path == "report.xlsx"
        assert "Excel" in str(error)
    
    def test_device_connection_error(self):
        """Тест ошибки подключения к устройству"""
        error = DeviceConnectionError("192.168.1.1", 80)
        assert error.host == "192.168.1.1"
        assert error.port == 80
        assert "192.168.1.1" in str(error)
    
    def test_exception_inheritance(self):
        """Тест иерархии исключений"""
        assert issubclass(ConfigError, LogStormError)
        assert issubclass(DataError, LogStormError)
        assert issubclass(AnalysisError, LogStormError)
        assert issubclass(ExportError, LogStormError)
        assert issubclass(DeviceError, LogStormError)

    def test_config_validation_error(self):
        """Тест ошибки валидации конфигурации"""
        error = ConfigValidationError("timeout", -5, "положительное число")
        assert error.field == "timeout"
        assert error.value == -5
        assert "timeout" in str(error)

    def test_empty_data_error(self):
        """Тест ошибки пустых данных"""
        error = EmptyDataError("events.ndjson")
        assert error.source == "events.ndjson"
        assert "Нет данных" in str(error)

    def test_schedule_error(self):
        """Тест ошибки расписания"""
        error = ScheduleError("user123", "Неверный день недели")
        assert error.person_id == "user123"
        assert "Неверный день недели" in str(error)

    def test_excel_export_error(self):
        """Тест ошибки экспорта Excel"""
        error = ExcelExportError("report.xlsx", "Недостаточно памяти")
        assert error.file_path == "report.xlsx"
        assert "Недостаточно памяти" in str(error)

    def test_device_auth_error(self):
        """Тест ошибки авторизации на устройстве"""
        error = DeviceAuthError("192.168.1.1")
        assert error.host == "192.168.1.1"
        assert "авторизации" in str(error)


class TestLogging:
    """Тесты логирования"""

    def test_get_logger(self):
        """Тест получения логгера"""
        log = get_logger('test')
        assert log is not None
        assert log.name == 'test'

    def test_setup_logging(self):
        """Тест настройки логирования"""
        log = setup_logging(logging.DEBUG, console=False)
        assert log is not None
        assert log.level == logging.DEBUG

    def test_init_logging_verbose(self):
        """Тест инициализации с verbose=True"""
        log = init_logging(verbose=True)
        assert log.level == logging.DEBUG

    def test_init_logging_normal(self):
        """Тест инициализации с verbose=False"""
        log = init_logging(verbose=False)
        assert log.level == logging.INFO


class TestExceptionHandling:
    """Тесты обработки исключений"""

    def test_catch_specific_exception(self):
        """Тест перехвата конкретного исключения"""
        with pytest.raises(ConfigFileNotFoundError) as exc_info:
            raise ConfigFileNotFoundError("/missing/file.json")

        assert exc_info.value.file_path == "/missing/file.json"

    def test_catch_base_exception(self):
        """Тест перехвата через базовый класс"""
        with pytest.raises(LogStormError):
            raise PersonNotFoundError("test_user")

    def test_catch_standard_exception(self):
        """Тест что LogStormError наследуется от Exception"""
        with pytest.raises(Exception):
            raise DeviceConnectionError("localhost")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
