"""
LogStorm Logging - централизованное логирование
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


# Форматтер для консоли (цветной)
class ColoredFormatter(logging.Formatter):
    """Цветной форматтер для консоли"""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    console: bool = True
) -> logging.Logger:
    """
    Настройка логирования для приложения.
    
    Args:
        level: Уровень логирования (DEBUG, INFO, WARNING, ERROR)
        log_file: Путь к файлу логов (опционально)
        console: Выводить ли логи в консоль
    
    Returns:
        Настроенный logger
    
    Пример:
        logger = setup_logging(logging.DEBUG, 'logs/app.log')
        logger.info("Приложение запущено")
    """
    logger = logging.getLogger('logstorm')
    logger.setLevel(level)
    
    # Очищаем существующие хендлеры
    logger.handlers.clear()
    
    # Формат для файла (без цветов)
    file_format = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Формат для консоли (с цветами)
    console_format = ColoredFormatter(
        '%(levelname)s | %(message)s'
    )
    
    # Консольный хендлер
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_format)
        console_handler.setLevel(level)
        logger.addHandler(console_handler)
    
    # Файловый хендлер
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(
            log_path, encoding='utf-8'
        )
        file_handler.setFormatter(file_format)
        file_handler.setLevel(level)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = 'logstorm') -> logging.Logger:
    """
    Получить logger для модуля.
    
    Args:
        name: Имя модуля (например, 'logstorm.gui' или 'logstorm.services')
    
    Returns:
        Logger для модуля
    
    Пример:
        logger = get_logger('logstorm.services.data_loader')
        logger.debug("Загрузка файла...")
    """
    return logging.getLogger(name)


# Инициализация при импорте
_default_logger: Optional[logging.Logger] = None


def init_logging(
    verbose: bool = False,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Инициализировать логирование для приложения.
    
    Args:
        verbose: True для DEBUG, False для INFO
        log_file: Опциональный путь к файлу логов
    
    Returns:
        Настроенный logger
    """
    global _default_logger
    
    level = logging.DEBUG if verbose else logging.INFO
    
    # Генерируем имя файла если не указано
    if log_file is None:
        timestamp = datetime.now().strftime('%Y%m%d')
        log_file = f'logs/logstorm_{timestamp}.log'
    
    _default_logger = setup_logging(level, log_file, console=True)
    return _default_logger


def logger() -> logging.Logger:
    """
    Получить глобальный logger.
    
    Returns:
        Глобальный logger (создаётся при первом вызове)
    """
    global _default_logger
    if _default_logger is None:
        _default_logger = init_logging()
    return _default_logger
