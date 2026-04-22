# Использование SQLite для анализа данных

## Обзор

С версии 2.0 LogStorm поддерживает загрузку событий из SQLite базы данных, которую создаёт коллектор. Это значительно ускоряет работу с большими объёмами данных.

## Преимущества SQLite

- **Быстрая фильтрация**: запросы по датам и устройствам выполняются мгновенно
- **Меньше памяти**: загружаются только нужные события
- **Статистика**: быстрый доступ к метрикам (количество событий, устройств, сотрудников)
- **Совместимость**: работает параллельно с NDJSON

## Использование в коде

### Базовая загрузка

```python
from analyzer.data_loader import DataLoader

# Загрузка всех событий из БД
df = DataLoader.load_logs(
    'data/events.db',
    file_type='sqlite'
)
```

### Загрузка с фильтрацией

```python
from analyzer.data_loader import DataLoader

# Загрузка событий из SQLite
df = DataLoader.load_logs(
    'data/events.db',
    file_type='sqlite'
)
```

Фильтрация по сотруднику, периоду и устройству выполняется на уровне
`core.repositories.CollectorEventRepository`. `DataLoader` отвечает за
нормализацию CSV, NDJSON и SQLite в общий формат анализа.

### Использование с PersonMapper

```python
from analyzer.data_loader import DataLoader
from analyzer.person_mapper import PersonMapper

mapper = PersonMapper('data/person.sample.json')

df = DataLoader.load_logs(
    'data/events.db',
    file_type='sqlite',
    person_mapper=mapper
)
```

### Прямое использование repository

```python
from core.repositories import CollectorEventRepository
from datetime import date

repo = CollectorEventRepository('data/events.db')

# Загрузка событий
events = repo.load_raw_events(
    period_start=date(2025, 12, 1),
    period_end=date(2025, 12, 24)
)

# События одного сотрудника
employee_events = repo.load_raw_events(employee_id='42')
```

## Использование в API и CLI

Основной путь работы: `python main.py analyze`, `python main.py api` и
collector. GUI удален из активного проекта.

## Миграция с NDJSON

Если у вас уже есть NDJSON файлы, коллектор автоматически создаст SQLite БД при следующем запуске. Оба формата будут синхронизироваться.

### Ручная миграция

Если нужно создать SQLite из существующих NDJSON:

```python
from collector.storage import EventStorage
import json

storage = EventStorage(
    ndjson_path='data/events.ndjson',
    sqlite_path='data/events.db'
)

# Загрузка событий из NDJSON
events = []
with open('data/events.ndjson', 'r', encoding='utf-8') as f:
    for line in f:
        events.append(json.loads(line))

# Запись в БД
storage.write_events(events)
```

## Структура БД

### Таблица `events`

| Колонка | Тип | Описание |
|---------|-----|----------|
| `device` | TEXT | IP адрес устройства |
| `serialNo` | INTEGER | Serial номер события |
| `time` | TEXT | Время события (ISO 8601) |
| `employeeNoString` | TEXT | Табельный номер |
| `name` | TEXT | Имя сотрудника |
| `event_data` | TEXT | Полные данные события (JSON) |
| `collected_at` | TEXT | Время сбора события |

**PRIMARY KEY**: (`device`, `serialNo`)

### Таблица `collector_state`

Хранит состояние сборщика для каждого устройства:
- `last_serial` - последний собранный serial
- `last_collect` - время последнего сбора

## Производительность

Сравнение времени загрузки 100,000 событий:

| Источник | Время | Память |
|----------|-------|---------|
| NDJSON | ~15 сек | ~500 MB |
| SQLite (все) | ~3 сек | ~300 MB |
| SQLite (фильтр) | ~0.5 сек | ~50 MB |

## Обратная совместимость

`DataLoader` автоматически определяет тип источника:

```python
# Автоопределение по расширению
df = DataLoader.load_logs('data/events.db')  # SQLite
df = DataLoader.load_logs('data/events.ndjson')  # NDJSON
df = DataLoader.load_logs('data/attendance.csv')  # CSV
```

Старые импорты из `services` больше не поддерживаются.
