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
from services import DataLoader

# Загрузка всех событий из БД
df = DataLoader.load_logs(
    'data/events.db',
    file_type='sqlite'
)
```

### Загрузка с фильтрацией

```python
from datetime import date
from services import DataLoader

# Загрузка событий за период
df = DataLoader.load_logs(
    'data/events.db',
    file_type='sqlite',
    start_date=date(2025, 12, 1),
    end_date=date(2025, 12, 24)
)

# Загрузка с конкретных камер
df = DataLoader.load_logs(
    'data/events.db',
    file_type='sqlite',
    devices=['192.168.1.101', '192.168.1.102']
)

# Комбинированная фильтрация
df = DataLoader.load_logs(
    'data/events.db',
    file_type='sqlite',
    start_date=date(2025, 12, 1),
    end_date=date(2025, 12, 24),
    devices=['192.168.1.101']
)
```

### Использование с PersonMapper

```python
from services import DataLoader, PersonMapper

mapper = PersonMapper('person.json')

df = DataLoader.load_logs(
    'data/events.db',
    file_type='sqlite',
    person_mapper=mapper
)
```

### Прямое использование SQLiteLoader

```python
from services import SQLiteLoader
from datetime import date

loader = SQLiteLoader('data/events.db')

# Загрузка событий
df = loader.load_events(
    start_date=date(2025, 12, 1),
    end_date=date(2025, 12, 24)
)

# Получение списка устройств
devices = loader.get_device_list()
# [{'host': '192.168.1.101', 'name': 'Камера входа'}, ...]

# Получение диапазона дат
min_date, max_date = loader.get_date_range()

# Статистика
stats = loader.get_stats()
print(f"Всего событий: {stats['total_events']}")
print(f"Устройств: {stats['total_devices']}")
print(f"Сотрудников: {stats['total_employees']}")
```

## Использование в GUI

В GUI приложении (`run_gui.py`) теперь можно выбрать источник данных:

1. **SQLite база** - рекомендуется для больших объёмов
2. **NDJSON файлы** - для совместимости и экспорта

### Настройка в config.json

```json
{
  "data_source": {
    "type": "sqlite",
    "path": "//172.11.1.254/Face_ID/data/events.db"
  },
  "files": [
    "//172.11.1.254/Face_ID/logs/events.ndjson"
  ],
  "prefs_file": "person.json"
}
```

## Миграция с NDJSON

Если у вас уже есть NDJSON файлы, коллектор автоматически создаст SQLite БД при следующем запуске. Оба формата будут синхронизироваться.

### Ручная миграция

Если нужно создать SQLite из существующих NDJSON:

```python
from collector.storage import EventStorage
import json

storage = EventStorage(
    ndjson_file='data/events.ndjson',
    sqlite_file='data/events.db'
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
| `serial` | INTEGER | Serial номер события |
| `time` | TEXT | Время события (ISO 8601) |
| `name` | TEXT | Имя сотрудника |
| `employeeNoString` | TEXT | Табельный номер |
| `major` | INTEGER | Тип события (5 = проход) |
| `minor` | INTEGER | Подтип события |
| `device_name` | TEXT | Название устройства |
| `event_data` | TEXT | Полные данные события (JSON) |

**PRIMARY KEY**: (`device`, `serial`)

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

Все существующие скрипты продолжат работать без изменений!
