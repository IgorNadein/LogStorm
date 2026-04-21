# 🔧 Мастер-план полного рефакторинга LogStorm

**Дата создания**: 22 декабря 2025 г.  
**Статус**: В планировании  
**Версия проекта**: 2.9.3+

---

## 📊 Текущее состояние проекта

### Статистика кодовой базы
```
Общее количество Python файлов: ~40
Строк кода в основных модулях: ~6000+
Самые большие файлы:
  - gui_app_fluent.py: 1991 строка (❗ монолит)
  - tools/app.py: 1373 строки (❗ монолит)
  - tools/manage_mapping.py: 374 строки
  - reporters/excel_formatter.py: 275 строк
```

### Архитектурные проблемы
1. **Монолитный GUI** - 1991 строка в одном файле
2. **Дублирование кода** - export_acs_events.py в двух местах
3. **Смешанная ответственность** - GUI содержит бизнес-логику
4. **Отсутствие dependency injection**
5. **Слабое покрытие тестами**
6. **Неоднородная структура** - разные стили кода

---

## 🎯 Цели рефакторинга

### Краткосрочные (1-2 недели)
- ✅ Организовать корневую папку (ВЫПОЛНЕНО)
- 🔄 Разделить монолитный GUI на компоненты
- 🔄 Централизовать конфигурацию
- 🔄 Унифицировать обработку ошибок

### Среднесрочные (1 месяц)
- Внедрить dependency injection
- Добавить полноценное логирование
- Написать unit-тесты (покрытие >70%)
- Документировать API всех модулей

### Долгосрочные (2-3 месяца)
- Полная типизация (mypy strict mode)
- Integration tests
- Performance profiling и оптимизация
- CI/CD pipeline

---

## 📋 Фазы рефакторинга

## Фаза 1: Декомпозиция GUI (ПРИОРИТЕТ: ВЫСОКИЙ)

### Проблема
`gui_app_fluent.py` содержит 1991 строку - это **монолитный файл** со смешанной ответственностью.

### Текущая структура
```python
gui_app_fluent.py (1991 строк)
├── AnalysisWorker (QThread)
├── PersonDialog 
├── AppState (состояние приложения)
├── SettingsInterface
├── PersonsInterface
├── LogDownloadWorker (QThread)
├── LogsInterface
├── ExportInterface
├── AnalysisInterface
├── AboutInterface
└── LogStormWindow (главное окно)
```

### План действий

#### 1.1 Создать структуру GUI компонентов
```
gui/
├── __init__.py
├── main_window.py           # Главное окно (LogStormWindow)
├── state/
│   ├── __init__.py
│   └── app_state.py         # AppState
├── interfaces/
│   ├── __init__.py
│   ├── settings.py          # SettingsInterface
│   ├── persons.py           # PersonsInterface
│   ├── logs.py              # LogsInterface
│   ├── analysis.py          # AnalysisInterface
│   ├── export.py            # ExportInterface
│   └── about.py             # AboutInterface
├── dialogs/
│   ├── __init__.py
│   └── person_dialog.py     # PersonDialog
└── workers/
    ├── __init__.py
    ├── analysis_worker.py   # AnalysisWorker
    └── log_download_worker.py  # LogDownloadWorker
```

#### 1.2 Рефакторинг по шагам
**Шаг 1**: Вынести workers (2 класса, ~150 строк)
```bash
# Создать gui/workers/
# Переместить AnalysisWorker → analysis_worker.py
# Переместить LogDownloadWorker → log_download_worker.py
```

**Шаг 2**: Вынести dialogs (1 класс, ~100 строк)
```bash
# Создать gui/dialogs/
# Переместить PersonDialog → person_dialog.py
```

**Шаг 3**: Вынести state (1 класс, ~150 строк)
```bash
# Создать gui/state/
# Переместить AppState → app_state.py
```

**Шаг 4**: Вынести interfaces (6 классов, ~1200 строк)
```bash
# Создать gui/interfaces/
# Каждый интерфейс в отдельный файл (~150-250 строк каждый)
```

**Шаг 5**: Создать main_window.py (~300 строк)
```bash
# Главное окно с навигацией и инициализацией
# Импорт всех интерфейсов
```

**Шаг 6**: Обновить run_gui.py
```python
# Было:
from gui_app_fluent import main

# Станет:
from gui.main_window import main
```

#### 1.3 Ожидаемый результат
```
До:  gui_app_fluent.py (1991 строка)
После: gui/ (11 файлов по 100-250 строк)
```

**Преимущества**:
- ✅ Легче поддерживать
- ✅ Легче тестировать
- ✅ Легче добавлять новые интерфейсы
- ✅ Меньше merge conflicts

---

## Фаза 2: Унификация конфигурации (ПРИОРИТЕТ: ВЫСОКИЙ)

### Проблема
Настройки разбросаны по разным местам:
- `config.py` - пороговые значения
- `config.json` - настройки GUI
- `person_mapping.json` - данные сотрудников
- Хардкод в коде

### План действий

#### 2.1 Создать централизованную конфигурацию
```python
config/
├── __init__.py
├── base.py              # Базовые настройки
├── analysis.py          # Настройки анализа
├── formatting.py        # Форматирование Excel
├── gui.py               # Настройки GUI
└── validators.py        # Пороги валидаторов
```

#### 2.2 Создать config manager
```python
# config/manager.py
class ConfigManager:
    """Централизованное управление конфигурацией"""
    
    def __init__(self):
        self.analysis = AnalysisConfig()
        self.formatting = FormattingConfig()
        self.gui = GuiConfig()
        
    @classmethod
    def from_files(cls, config_dir: Path):
        """Загрузка из файлов"""
        pass
    
    def validate(self) -> List[str]:
        """Валидация конфигурации"""
        pass
```

#### 2.3 Рефакторинг импортов
```python
# Было:
from config import LATE_THRESHOLD_MINUTES

# Станет:
from config import config_manager
late_threshold = config_manager.analysis.late_threshold_minutes
```

---

## Фаза 3: Обработка ошибок и логирование (ПРИОРИТЕТ: СРЕДНИЙ)

### Проблема
- Непоследовательная обработка ошибок
- Отсутствие централизованного логирования
- `print()` вместо logger
- Трудно отлаживать проблемы пользователей

### План действий

#### 3.1 Настроить логирование
```python
# utils/logging.py
import logging
from pathlib import Path

def setup_logging(log_dir: Path, level=logging.INFO):
    """Настройка логирования"""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / 'logstorm.log'),
            logging.StreamHandler()
        ]
    )
```

#### 3.2 Создать custom exceptions
```python
# exceptions.py
class LogStormError(Exception):
    """Базовое исключение"""
    pass

class ConfigError(LogStormError):
    """Ошибка конфигурации"""
    pass

class DataLoadError(LogStormError):
    """Ошибка загрузки данных"""
    pass

class AnalysisError(LogStormError):
    """Ошибка анализа"""
    pass
```

#### 3.3 Заменить print на logger
```python
# Было:
print(f"Загрузка prefs из: {self.prefs_file}")

# Станет:
logger.info("Загрузка prefs", extra={'file': self.prefs_file})
```

---

## Фаза 4: Dependency Injection (ПРИОРИТЕТ: СРЕДНИЙ)

### Проблема
- Жесткие связи между модулями
- Трудно тестировать
- Невозможно подменить зависимости

### План действий

#### 4.1 Установить dependency injection
```bash
pip install dependency-injector
```

#### 4.2 Создать контейнеры
```python
# di_container.py
from dependency_injector import containers, providers

class Container(containers.DeclarativeContainer):
    config = providers.Configuration()
    
    # Services
    data_loader = providers.Singleton(
        DataLoader,
        config=config.data_loader
    )
    
    attendance_service = providers.Factory(
        AttendanceService,
        data_loader=data_loader
    )
    
    # Reporters
    excel_reporter = providers.Factory(
        ExcelReporter,
        config=config.excel
    )
```

#### 4.3 Внедрить в GUI
```python
# gui/main_window.py
class LogStormWindow(FluentWindow):
    def __init__(self, container: Container):
        super().__init__()
        self.container = container
        self._init_services()
```

---

## Фаза 5: Тестирование (ПРИОРИТЕТ: ВЫСОКИЙ)

### Проблема
- Минимальное покрытие тестами
- Нет CI/CD
- Регрессии при изменениях

### План действий

#### 5.1 Структура тестов
```
tests/
├── unit/                    # Unit тесты
│   ├── test_analyzers.py
│   ├── test_models.py
│   ├── test_services.py
│   ├── test_reporters.py
│   └── test_validators.py
├── integration/             # Integration тесты
│   ├── test_data_flow.py
│   └── test_excel_export.py
├── fixtures/                # Тестовые данные
│   ├── sample_logs.csv
│   └── sample_mapping.json
└── conftest.py             # Pytest конфигурация
```

#### 5.2 Написать unit-тесты
```python
# tests/unit/test_analyzers.py
import pytest
from analyzer import StatusAnalyzer
from core.models import AttendanceRecord

def test_analyze_late_workday():
    """Тест опоздания в рабочий день"""
    record = AttendanceRecord(
        date=date(2025, 1, 15),  # Wednesday
        is_workday=True,
        arrival_time=time(9, 30),
        schedule_start=time(9, 0)
    )
    
    is_late, minutes = StatusAnalyzer.analyze_late(record)
    
    assert is_late is True
    assert minutes == 30

def test_no_late_weekend():
    """Опоздание не учитывается в выходной"""
    record = AttendanceRecord(
        date=date(2025, 1, 11),  # Saturday
        is_workday=False,
        arrival_time=time(10, 0),
        schedule_start=time(9, 0)
    )
    
    is_late, minutes = StatusAnalyzer.analyze_late(record)
    
    assert is_late is False
    assert minutes == 0
```

#### 5.3 Настроить pytest
```ini
# pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --verbose
    --cov=.
    --cov-report=html
    --cov-report=term
```

#### 5.4 Цели покрытия
- **Analyzers**: 90%+
- **Models**: 95%+
- **Services**: 80%+
- **Validators**: 90%+
- **Reporters**: 70%+
- **GUI**: 50%+ (базовые сценарии)

---

## Фаза 6: Типизация (ПРИОРИТЕТ: НИЗКИЙ)

### Проблема
- Неполная типизация
- Нет проверки типов в CI
- Ошибки типов находятся только в runtime

### План действий

#### 6.1 Настроить mypy
```ini
# mypy.ini
[mypy]
python_version = 3.11
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
disallow_incomplete_defs = True
check_untyped_defs = True
no_implicit_optional = True
warn_redundant_casts = True
warn_unused_ignores = True
warn_no_return = True
```

#### 6.2 Добавить типы постепенно
```python
# Было:
def analyze_late(record):
    if not record.is_workday:
        return False, 0

# Станет:
def analyze_late(record: AttendanceRecord) -> Tuple[bool, int]:
    if not record.is_workday:
        return False, 0
```

#### 6.3 Использовать Protocol для интерфейсов
```python
from typing import Protocol

class DataLoaderProtocol(Protocol):
    def load_logs(self, files: List[Path]) -> pd.DataFrame:
        ...

class AttendanceServiceProtocol(Protocol):
    def analyze_all(self) -> List[AttendanceRecord]:
        ...
```

---

## Фаза 7: Документация API (ПРИОРИТЕТ: СРЕДНИЙ)

### Проблема
- Неполная документация модулей
- Нет автоматической генерации API docs

### План действий

#### 7.1 Добавить docstrings
```python
def analyze_late(record: AttendanceRecord) -> Tuple[bool, int]:
    """
    Анализирует опоздание сотрудника.
    
    Проверяет время прихода относительно графика. Опоздание учитывается
    только для рабочих дней и если превышает порог LATE_THRESHOLD_MINUTES.
    
    Args:
        record: Запись посещения с информацией о дне и времени
        
    Returns:
        Кортеж (is_late, late_minutes):
            - is_late: True если есть опоздание
            - late_minutes: Количество минут опоздания
            
    Example:
        >>> record = AttendanceRecord(
        ...     is_workday=True,
        ...     arrival_time=time(9, 30),
        ...     schedule_start=time(9, 0)
        ... )
        >>> is_late, minutes = analyze_late(record)
        >>> assert is_late is True
        >>> assert minutes == 30
    """
```

#### 7.2 Настроить Sphinx
```bash
pip install sphinx sphinx-rtd-theme
sphinx-quickstart docs/
```

#### 7.3 Генерировать документацию
```bash
cd docs/
make html
```

---

## Фаза 8: Performance optimization (ПРИОРИТЕТ: НИЗКИЙ)

### Проблема
- Нет профилирования
- Потенциальные узкие места в обработке больших файлов

### План действий

#### 8.1 Профилирование
```python
# tools/profiler.py
import cProfile
import pstats

def profile_analysis():
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Код анализа
    service = AttendanceService(df, prefs)
    results = service.analyze_all()
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)
```

#### 8.2 Оптимизация pandas
```python
# Использовать категориальные типы для повторяющихся значений
df['user_name'] = df['user_name'].astype('category')

# Векторизация вместо apply
df['is_late'] = (df['arrival_time'] > df['schedule_start']).astype(bool)
```

#### 8.3 Кеширование
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_work_schedule(user_id: str) -> WorkSchedule:
    """Кешированное получение графика"""
    return WorkSchedule.from_preferences(prefs[user_id])
```

---

## 📅 Временная шкала

### Неделя 1-2: Декомпозиция GUI
- [ ] День 1-2: Вынести workers и dialogs
- [ ] День 3-4: Вынести state и interfaces
- [ ] День 5-7: Создать main_window, обновить импорты
- [ ] День 8-10: Тестирование, исправление багов

### Неделя 3: Конфигурация и ошибки
- [ ] День 1-2: Создать config manager
- [ ] День 3-4: Настроить логирование
- [ ] День 5: Создать custom exceptions
- [ ] День 6-7: Рефакторинг обработки ошибок

### Неделя 4: Тестирование
- [ ] День 1-3: Написать unit-тесты (analyzers, models)
- [ ] День 4-5: Написать unit-тесты (services, validators)
- [ ] День 6-7: Integration тесты

### Месяц 2: DI и типизация
- [ ] Неделя 1: Внедрить dependency injection
- [ ] Неделя 2-3: Добавить типы, настроить mypy
- [ ] Неделя 4: Документация API

### Месяц 3: Оптимизация
- [ ] Неделя 1: Профилирование
- [ ] Неделя 2: Оптимизация узких мест
- [ ] Неделя 3-4: CI/CD, финальное тестирование

---

## 🎯 Метрики успеха

### Код
- [ ] Нет файлов >500 строк
- [ ] Покрытие тестами >70%
- [ ] Все тесты проходят
- [ ] mypy без ошибок
- [ ] pylint score >9.0

### Документация
- [ ] API docs сгенерированы
- [ ] Все публичные функции задокументированы
- [ ] README актуален
- [ ] Есть примеры использования

### Производительность
- [ ] Анализ 1000 записей <1 сек
- [ ] Генерация Excel <5 сек
- [ ] GUI отзывчивый (<100ms на действие)

---

## 🚨 Риски и митигация

### Риск 1: Большой объем изменений
**Вероятность**: Высокая  
**Влияние**: Высокое  
**Митигация**:
- Делать маленькие PR
- Тестировать каждый шаг
- Поддерживать обратную совместимость

### Риск 2: Регрессии
**Вероятность**: Средняя  
**Влияние**: Высокое  
**Митигация**:
- Писать тесты до рефакторинга
- Использовать Git bisect
- Делать backup перед большими изменениями

### Риск 3: Конфликты слияния
**Вероятность**: Средняя  
**Влияние**: Среднее  
**Митигация**:
- Работать в feature branches
- Часто мержить в main
- Использовать rebase

---

## 📦 Необходимые зависимости

```txt
# Для DI
dependency-injector==4.41.0

# Для тестирования
pytest==7.4.0
pytest-cov==4.1.0
pytest-mock==3.11.1

# Для типизации
mypy==1.5.0
types-openpyxl

# Для документации
sphinx==7.1.0
sphinx-rtd-theme==1.3.0

# Для профилирования
memory-profiler==0.61.0
```

---

## 🔄 Стратегия миграции

### Принципы
1. **Инкрементальность** - малые изменения, часто
2. **Обратная совместимость** - старый код работает
3. **Тестирование** - тесты перед рефакторингом
4. **Документирование** - фиксировать изменения

### Процесс
1. Создать feature branch
2. Написать тесты для текущего поведения
3. Выполнить рефакторинг
4. Убедиться что тесты проходят
5. Создать PR с описанием изменений
6. Code review
7. Merge в main

---

## 📝 Следующие шаги

### Немедленные действия
1. [ ] Создать `refactoring/phase1` branch
2. [ ] Сделать backup текущей версии
3. [ ] Начать с Фазы 1: Декомпозиция GUI
4. [ ] Создать `gui/` структуру папок

### Чек-лист перед началом
- [x] План рефакторинга утвержден
- [ ] Backup создан
- [ ] Все текущие изменения закоммичены
- [ ] Зависимости установлены
- [ ] Тестовое окружение настроено

---

**Автор плана**: GitHub Copilot  
**Статус**: Готов к исполнению  
**Приоритет**: Высокий  
**Ожидаемое время**: 2-3 месяца

**Начинаем с Фазы 1: Декомпозиция GUI → gui_app_fluent.py (1991 строка)**
