# LogStorm Collector

Фоновый сборщик событий СКУД с камер Hikvision.

## Новые возможности ✨

### Двойное хранилище (NDJSON + SQLite)

События теперь записываются **одновременно** в два формата:

1. **NDJSON файл** (`events.ndjson`)
   - Построчный JSON, удобен для бэкапа
   - Читается стандартными утилитами
   - Совместим со старыми версиями

2. **SQLite БД** (`events.db`)
   - Мгновенный поиск по индексам
   - Автоматическая дедупликация (PRIMARY KEY)
   - Запросы SQL для аналитики
   - **Хранит состояние коллектора** (таблица `collector_state`)

### Состояние в SQLite (без JSON файла)

Вся информация о состоянии сбора хранится в SQLite:

```sql
CREATE TABLE collector_state (
    device TEXT PRIMARY KEY,
    last_serial INTEGER NOT NULL,
    last_collect TEXT,
    updated_at TEXT NOT NULL
);
```

**Преимущества:**
- ✅ **Нет рассинхрона** — одно место истины
- ✅ **ACID гарантии** — транзакции на уровне БД
- ✅ **Защита от дубликатов** — PRIMARY KEY не даст записать повторно
- ✅ **Безопасность при параллельном запуске** — блокировки SQLite
- ✅ **Автоматическое восстановление** — состояние всегда актуально

## Использование

### Обычный запуск

```bash
python collector.py --config collector.json --verbose
```

События записываются в:
- `//172.11.1.254/Face_ID/logs/events.ndjson`
- `//172.11.1.254/Face_ID/logs/events.db` ← автоматически создаётся

### Восстановление SQLite из NDJSON

Если SQLite БД повреждена или удалена:

```bash
python rebuild_sqlite.py //172.11.1.254/Face_ID/logs/events.ndjson
```

Результат:
```
Восстановление SQLite из events.ndjson...
  Обработано: 150,000 событий...
✅ Готово! Импортировано 150,000 событий
📊 SQLite БД: events.db

📋 Последние serialNo по устройствам:
  192.168.1.101: 106,213 (всего событий: 45,123)
  192.168.1.102: 58,650 (всего событий: 32,456)
  192.168.1.103: 114,309 (всего событий: 51,234)
  192.168.1.104: 27,835 (всего событий: 21,187)
```

### Проверка состояния

```python
from storage import EventStorage

storage = EventStorage('//172.11.1.254/Face_ID/logs/events.ndjson')

# Последний serialNo для камеры
last = storage.get_last_serial('192.168.1.101')
print(f"Last serial: {last}")

# Все устройства
serials = storage.get_last_serials_all_devices()
for device, serial in serials.items():
    count = storage.get_event_count(device)
    print(f"{device}: {serial} ({count} событий)")
```

## Конфигурация

В `collector.json` используйте секцию `storage` для настройки хранилища:

```json
{
  "storage": {
    "ndjson": "//172.11.1.254/Face_ID/data/logs/events.ndjson",
    "sqlite": "//172.11.1.254/Face_ID/data/events.db"
  },
  "log_file": "collector.log",
  "interval_minutes": 15,
  ...
}
```

**Параметры секции `storage`:**

- `ndjson` — путь к NDJSON файлу (обязательный)
- `sqlite` — путь к SQLite БД (опциональный)
  - Если не указан → автоматически создаётся рядом с NDJSON

**Примеры:**

```json
// Минимальная конфигурация
{
  "storage": {
    "ndjson": "//server/logs/events.ndjson"
    // sqlite будет: //server/logs/events.db
  }
}

// Явное указание обоих файлов
{
  "storage": {
    "ndjson": "//server/logs/events.ndjson",
    "sqlite": "//server/db/collector.db"
  }
}

// Разные расположения для производительности
{
  "storage": {
    "ndjson": "//server/backup/events.ndjson",  // Сетевой диск (медленно, но безопасно)
    "sqlite": "C:/local/collector.db"           // Локальный диск (быстро)
  }
}
```

**Обратная совместимость:**

Старый формат также поддерживается:
```json
{
  "output_file": "//server/logs/events.ndjson",
  "sqlite_file": "//server/logs/events.db"
}
```

Но рекомендуется использовать новый формат с секцией `storage`.

### Индивидуальные настройки сохранения изображений

Каждая камера может иметь свою настройку `save_images`:

```json
{
  "images": {
    "enabled": true,  // глобальная настройка по умолчанию
    "folder": "//172.11.1.254/Face_ID/images",
    "format": "{date}/{employeeNoString}_{serialNo}.jpg"
  },
  "devices": [
    {
      "name": "Камера входа",
      "host": "192.168.1.101",
      "save_images": true   // ✅ сохраняем фото
    },
    {
      "name": "Камера 2",
      "host": "192.168.1.102",
      "save_images": false  // ❌ НЕ сохраняем фото
    },
    {
      "name": "Камера 3",
      "host": "192.168.1.103"
      // не указано → берётся из images.enabled
    }
  ]
}
```

**Приоритет:**
1. Если указано `device.save_images` → используется это значение
2. Иначе → используется `images.enabled`

**Применение:**
- Камеры входа/выхода → сохраняем фото (верификация)
- Внутренние камеры → только события (экономия места)

## Производительность

**Запись событий:**
- NDJSON only: ~100ms на 1000 событий
- NDJSON + SQLite: ~110ms на 1000 событий
- **Overhead: ~10%** (приемлемо)

**Поиск последнего serialNo:**
- NDJSON (весь файл 10GB): минуты
- NDJSON (конец файла): <1 секунда
- **SQLite с индексом: <0.01 секунды** ✅

## Схема БД

```sql
CREATE TABLE events (
    device TEXT NOT NULL,           -- IP камеры
    serialNo INTEGER NOT NULL,      -- Serial номер события
    time TEXT NOT NULL,             -- Время события
    employeeNoString TEXT,          -- ID сотрудника
    name TEXT,                      -- Имя сотрудника
    event_data TEXT NOT NULL,       -- Полные данные (JSON)
    collected_at TEXT NOT NULL,     -- Время сбора
    PRIMARY KEY (device, serialNo)
);

CREATE INDEX idx_device_serial ON events(device, serialNo DESC);
CREATE INDEX idx_time ON events(time);
```

## Миграция с NDJSON

Если у вас уже есть `events.ndjson`:

1. Просто запустите коллектор — SQLite создастся автоматически
2. Новые события будут писаться в оба формата
3. Для старых событий запустите `rebuild_sqlite.py`

**Не нужно:**
- ❌ Удалять NDJSON файл
- ❌ Менять конфигурацию
- ❌ Пересобирать всё вручную

Всё работает автоматически! 🚀
