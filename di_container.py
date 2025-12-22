"""
LogStorm DI Container - легковесная реализация Dependency Injection

Позволяет:
- Централизованно управлять зависимостями
- Легко подменять сервисы для тестирования
- Избежать жестких связей между модулями
"""

from typing import TypeVar, Type, Callable, Any, Optional, Dict
from functools import wraps
import inspect

T = TypeVar('T')


class ServiceContainer:
    """
    Контейнер для управления зависимостями.
    
    Поддерживает:
    - Singleton - один экземпляр на всё приложение
    - Factory - новый экземпляр при каждом запросе
    - Transient - аналог Factory
    
    Пример использования:
        container = ServiceContainer()
        container.register_singleton(ConfigManager, lambda: ConfigManager())
        container.register_factory(DataLoader, lambda c: DataLoader(c.get(ConfigManager)))
        
        config = container.get(ConfigManager)  # Singleton
        loader = container.get(DataLoader)     # Новый экземпляр
    """
    
    def __init__(self):
        self._singletons: Dict[type, Any] = {}
        self._factories: Dict[type, Callable[['ServiceContainer'], Any]] = {}
        self._singleton_factories: Dict[type, Callable[['ServiceContainer'], Any]] = {}
    
    def register_singleton(
        self,
        service_type: Type[T],
        factory: Optional[Callable[['ServiceContainer'], T]] = None,
        instance: Optional[T] = None
    ) -> 'ServiceContainer':
        """
        Регистрация singleton сервиса.
        
        Args:
            service_type: Тип сервиса
            factory: Фабрика для создания (вызывается один раз)
            instance: Готовый экземпляр (если factory не указан)
        
        Returns:
            self для цепочки вызовов
        
        Пример:
            container.register_singleton(ConfigManager, lambda c: ConfigManager())
            container.register_singleton(Logger, instance=my_logger)
        """
        if instance is not None:
            self._singletons[service_type] = instance
        elif factory is not None:
            self._singleton_factories[service_type] = factory
        else:
            # Автоматическое создание если конструктор без параметров
            self._singleton_factories[service_type] = lambda c: service_type()
        return self
    
    def register_factory(
        self,
        service_type: Type[T],
        factory: Callable[['ServiceContainer'], T]
    ) -> 'ServiceContainer':
        """
        Регистрация factory сервиса (новый экземпляр при каждом запросе).
        
        Args:
            service_type: Тип сервиса
            factory: Фабрика для создания
        
        Returns:
            self для цепочки вызовов
        
        Пример:
            container.register_factory(
                DataLoader, 
                lambda c: DataLoader(c.get(ConfigManager))
            )
        """
        self._factories[service_type] = factory
        return self
    
    def register_transient(
        self,
        service_type: Type[T],
        factory: Callable[['ServiceContainer'], T]
    ) -> 'ServiceContainer':
        """Синоним для register_factory"""
        return self.register_factory(service_type, factory)
    
    def get(self, service_type: Type[T]) -> T:
        """
        Получить экземпляр сервиса.
        
        Args:
            service_type: Тип сервиса
        
        Returns:
            Экземпляр сервиса
        
        Raises:
            KeyError: Если сервис не зарегистрирован
        
        Пример:
            config = container.get(ConfigManager)
        """
        # Проверяем singleton
        if service_type in self._singletons:
            return self._singletons[service_type]
        
        # Проверяем singleton factory (ленивая инициализация)
        if service_type in self._singleton_factories:
            instance = self._singleton_factories[service_type](self)
            self._singletons[service_type] = instance
            return instance
        
        # Проверяем factory
        if service_type in self._factories:
            return self._factories[service_type](self)
        
        raise KeyError(f"Сервис {service_type.__name__} не зарегистрирован")
    
    def has(self, service_type: Type) -> bool:
        """Проверить, зарегистрирован ли сервис"""
        return (
            service_type in self._singletons or
            service_type in self._singleton_factories or
            service_type in self._factories
        )
    
    def reset(self):
        """Сбросить все singleton экземпляры (полезно для тестов)"""
        self._singletons.clear()
    
    def override(
        self,
        service_type: Type[T],
        mock: T
    ) -> 'ServiceContainer':
        """
        Временно заменить сервис (для тестов).
        
        Args:
            service_type: Тип сервиса
            mock: Мок-объект
        
        Returns:
            self для цепочки вызовов
        
        Пример:
            container.override(DataLoader, MockDataLoader())
        """
        self._singletons[service_type] = mock
        return self


# Глобальный контейнер
_container: Optional[ServiceContainer] = None


def get_container() -> ServiceContainer:
    """Получить глобальный контейнер"""
    global _container
    if _container is None:
        _container = ServiceContainer()
    return _container


def set_container(container: ServiceContainer):
    """Установить глобальный контейнер"""
    global _container
    _container = container


def inject(func: Callable) -> Callable:
    """
    Декоратор для автоматической инъекции зависимостей.
    
    Анализирует type hints параметров и автоматически
    получает их из контейнера.
    
    Пример:
        @inject
        def analyze(data_loader: DataLoader, config: ConfigManager):
            # data_loader и config будут получены из контейнера
            pass
    """
    sig = inspect.signature(func)
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        container = get_container()
        
        # Собираем параметры с type hints
        for param_name, param in sig.parameters.items():
            if param_name not in kwargs and param.annotation != inspect.Parameter.empty:
                try:
                    kwargs[param_name] = container.get(param.annotation)
                except KeyError:
                    pass  # Параметр не зарегистрирован
        
        return func(*args, **kwargs)
    
    return wrapper


def injectable(cls: Type[T]) -> Type[T]:
    """
    Декоратор класса для автоматической регистрации в контейнере.
    
    Пример:
        @injectable
        class MyService:
            pass
        
        # Автоматически доступен как:
        container.get(MyService)
    """
    container = get_container()
    container.register_singleton(cls)
    return cls
