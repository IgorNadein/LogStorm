"""
LogStorm Exceptions - пользовательские исключения
"""


class LogStormError(Exception):
    """Базовое исключение для LogStorm"""
    
    def __init__(self, message: str, details: str = None):
        self.message = message
        self.details = details
        super().__init__(self.message)
    
    def __str__(self):
        if self.details:
            return f"{self.message}\n  Детали: {self.details}"
        return self.message


# === Ошибки конфигурации ===

class ConfigError(LogStormError):
    """Ошибка конфигурации"""
    pass


class ConfigFileNotFoundError(ConfigError):
    """Файл конфигурации не найден"""
    
    def __init__(self, file_path: str):
        super().__init__(
            f"Файл конфигурации не найден: {file_path}",
            "Проверьте путь к файлу и права доступа"
        )
        self.file_path = file_path


class ConfigValidationError(ConfigError):
    """Ошибка валидации конфигурации"""
    
    def __init__(self, field: str, value, expected: str):
        super().__init__(
            f"Некорректное значение поля '{field}': {value}",
            f"Ожидается: {expected}"
        )
        self.field = field
        self.value = value
        self.expected = expected


# === Ошибки данных ===

class DataError(LogStormError):
    """Ошибка данных"""
    pass


class FileNotFoundError(DataError):
    """Файл данных не найден"""
    
    def __init__(self, file_path: str):
        super().__init__(
            f"Файл не найден: {file_path}",
            "Проверьте путь к файлу"
        )
        self.file_path = file_path


class FileFormatError(DataError):
    """Некорректный формат файла"""
    
    def __init__(self, file_path: str, expected_format: str):
        super().__init__(
            f"Некорректный формат файла: {file_path}",
            f"Ожидается формат: {expected_format}"
        )
        self.file_path = file_path
        self.expected_format = expected_format


class EmptyDataError(DataError):
    """Пустые данные"""
    
    def __init__(self, source: str):
        super().__init__(
            f"Нет данных для обработки: {source}",
            "Проверьте входные файлы"
        )
        self.source = source


# === Ошибки анализа ===

class AnalysisError(LogStormError):
    """Ошибка анализа"""
    pass


class PersonNotFoundError(AnalysisError):
    """Сотрудник не найден"""
    
    def __init__(self, person_id: str):
        super().__init__(
            f"Сотрудник не найден: {person_id}",
            "Добавьте сотрудника в person_mapping.json"
        )
        self.person_id = person_id


class ScheduleError(AnalysisError):
    """Ошибка расписания"""
    
    def __init__(self, person_id: str, message: str):
        super().__init__(
            f"Ошибка расписания для {person_id}: {message}"
        )
        self.person_id = person_id


# === Ошибки экспорта ===

class ExportError(LogStormError):
    """Ошибка экспорта"""
    pass


class ExcelExportError(ExportError):
    """Ошибка экспорта в Excel"""
    
    def __init__(self, file_path: str, reason: str):
        super().__init__(
            f"Не удалось создать Excel файл: {file_path}",
            reason
        )
        self.file_path = file_path


class FileLockedError(ExportError):
    """Файл заблокирован"""
    
    def __init__(self, file_path: str):
        super().__init__(
            f"Файл заблокирован: {file_path}",
            "Закройте файл в Excel и попробуйте снова"
        )
        self.file_path = file_path


# === Ошибки устройства ===

class DeviceError(LogStormError):
    """Ошибка устройства"""
    pass


class DeviceConnectionError(DeviceError):
    """Ошибка подключения к устройству"""
    
    def __init__(self, host: str, port: int = 80):
        super().__init__(
            f"Не удалось подключиться к {host}:{port}",
            "Проверьте IP адрес, порт и сетевое подключение"
        )
        self.host = host
        self.port = port


class DeviceAuthError(DeviceError):
    """Ошибка авторизации на устройстве"""
    
    def __init__(self, host: str):
        super().__init__(
            f"Ошибка авторизации на {host}",
            "Проверьте логин и пароль"
        )
        self.host = host
