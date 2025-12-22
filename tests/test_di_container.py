"""
Тесты для DI контейнера
"""

import sys
import os

# Добавляем корневой каталог в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from di_container import (  # noqa: E402
    ServiceContainer,
    get_container,
    set_container,
    inject,
    injectable
)


class MockService:
    """Тестовый сервис"""
    def __init__(self, value: str = "default"):
        self.value = value


class MockDependentService:
    """Сервис с зависимостью"""
    def __init__(self, dependency: MockService):
        self.dependency = dependency


class TestServiceContainer:
    """Тесты ServiceContainer"""

    def test_register_singleton_with_instance(self):
        """Тест регистрации singleton с готовым экземпляром"""
        container = ServiceContainer()
        instance = MockService("test")
        container.register_singleton(MockService, instance=instance)

        result = container.get(MockService)
        assert result is instance
        assert result.value == "test"

    def test_register_singleton_with_factory(self):
        """Тест регистрации singleton с фабрикой"""
        container = ServiceContainer()
        container.register_singleton(
            MockService,
            lambda c: MockService("factory")
        )

        result1 = container.get(MockService)
        result2 = container.get(MockService)

        assert result1 is result2  # Один и тот же экземпляр
        assert result1.value == "factory"

    def test_register_factory(self):
        """Тест регистрации factory (новый экземпляр каждый раз)"""
        container = ServiceContainer()
        counter = [0]

        def factory(c):
            counter[0] += 1
            return MockService(f"instance_{counter[0]}")

        container.register_factory(MockService, factory)

        result1 = container.get(MockService)
        result2 = container.get(MockService)

        assert result1 is not result2  # Разные экземпляры
        assert result1.value == "instance_1"
        assert result2.value == "instance_2"

    def test_get_unregistered_raises(self):
        """Тест что get выбрасывает исключение для незарегистрированного"""
        container = ServiceContainer()

        with pytest.raises(KeyError) as exc_info:
            container.get(MockService)

        assert "MockService" in str(exc_info.value)

    def test_has(self):
        """Тест проверки регистрации"""
        container = ServiceContainer()
        assert not container.has(MockService)

        container.register_singleton(MockService, instance=MockService())
        assert container.has(MockService)

    def test_reset(self):
        """Тест сброса singleton экземпляров"""
        container = ServiceContainer()
        container.register_singleton(
            MockService,
            lambda c: MockService("original")
        )

        instance1 = container.get(MockService)
        assert instance1.value == "original"

        container.reset()

        instance2 = container.get(MockService)
        assert instance2 is not instance1  # Новый экземпляр

    def test_override(self):
        """Тест подмены сервиса (для тестов)"""
        container = ServiceContainer()
        container.register_singleton(
            MockService,
            lambda c: MockService("original")
        )

        original = container.get(MockService)
        assert original.value == "original"

        mock = MockService("mocked")
        container.override(MockService, mock)

        result = container.get(MockService)
        assert result is mock
        assert result.value == "mocked"

    def test_chain_registration(self):
        """Тест цепочки регистраций"""
        container = (
            ServiceContainer()
            .register_singleton(MockService, instance=MockService("a"))
            .register_factory(str, lambda c: "factory")
        )

        assert container.get(MockService).value == "a"
        assert container.get(str) == "factory"

    def test_dependency_injection(self):
        """Тест инъекции зависимостей"""
        container = ServiceContainer()
        container.register_singleton(
            MockService,
            lambda c: MockService("injected")
        )
        container.register_factory(
            MockDependentService,
            lambda c: MockDependentService(c.get(MockService))
        )

        service = container.get(MockDependentService)
        assert service.dependency.value == "injected"


class TestGlobalContainer:
    """Тесты глобального контейнера"""

    def test_get_container(self):
        """Тест получения глобального контейнера"""
        container = get_container()
        assert container is not None
        assert isinstance(container, ServiceContainer)

    def test_set_container(self):
        """Тест установки глобального контейнера"""
        custom = ServiceContainer()
        custom.register_singleton(MockService, instance=MockService("custom"))

        set_container(custom)

        result = get_container()
        assert result is custom


class TestInjectDecorator:
    """Тесты декоратора @inject"""

    def test_inject_function(self):
        """Тест инъекции в функцию"""
        container = ServiceContainer()
        container.register_singleton(
            MockService,
            instance=MockService("injected")
        )
        set_container(container)

        @inject
        def my_function(service: MockService):
            return service.value

        result = my_function()
        assert result == "injected"

    def test_inject_with_explicit_arg(self):
        """Тест что явный аргумент имеет приоритет"""
        container = ServiceContainer()
        container.register_singleton(
            MockService,
            instance=MockService("container")
        )
        set_container(container)

        @inject
        def my_function(service: MockService):
            return service.value

        explicit = MockService("explicit")
        result = my_function(service=explicit)
        assert result == "explicit"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
