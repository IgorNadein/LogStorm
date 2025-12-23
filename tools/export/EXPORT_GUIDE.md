# 📥 Экспорт событий из СКУД Hikvision/HiWatch# 📥 Экспорт событий из СКУД Hikvision/HiWatch



## 🎯 Назначение## 🎯 Назначение



Инструменты для экспорта событий доступа из устройств Hikvision/HiWatch СКУД Инструменты для экспорта событий доступа из устройств Hikvision/HiWatch СКУД через ISAPI в формат NDJSON.

через ISAPI в формат NDJSON.

## 📋 Файлы

## 📋 Файлы

- **export_acs_events.py** - Основной скрипт экспорта событий

- **export_acs_events.py** - Основной скрипт экспорта событий- **test_performance.py** - Тесты производительности экспорта

- **export_split.py** - Экспорт с разделением на периоды- **EXPORT_GUIDE.md** - Эта инструкция

- **export_utils.py** - Общие утилиты (дедупликация, защита от перезаписи)

- **test_performance.py** - Тесты производительности экспорта## 🚀 Быстрый старт



## 🆕 Новые функции (v2.0)### Базовый экспорт (без изображений)



### 🛡️ Защита от перезаписи```bash

По умолчанию существующие файлы **НЕ перезаписываются**. python tools/export/export_acs_events.py \

Автоматически генерируется новое имя с timestamp.  --host 192.168.1.101 \

  --user admin \

```bash  --password your_password \

# Файл events.ndjson существует → создастся events_20251222_143000.ndjson  --start "2025-01-01T00:00:00" \

python export_acs_events.py --password CHANGE_ME --end 2025-12-15T23:59:59  --end "2025-12-31T23:59:59" \

  --out data/events.ndjson \

# Принудительная перезапись  --verbose

python export_acs_events.py --password CHANGE_ME --end 2025-12-15T23:59:59 --force```



# Резервная копия перед перезаписью### Экспорт с изображениями

python export_acs_events.py --password CHANGE_ME --end 2025-12-15T23:59:59 --force --backup

``````bash

python tools/export/export_acs_events.py \

### 🔄 Дедупликация событий  --host 192.168.1.101 \

Предотвращение записи дубликатов по `serialNo`:  --user admin \

  --password your_password \

```bash  --start "2025-01-01T00:00:00" \

# Включить дедупликацию  --end "2025-12-31T23:59:59" \

python export_acs_events.py --password CHANGE_ME --end 2025-12-15T23:59:59 --deduplicate  --pic \

  --out data/events_with_pic.ndjson \

# Дополнение существующего файла (автоматическая дедупликация)  --verbose

python export_acs_events.py --password CHANGE_ME --end 2025-12-15T23:59:59 --append```

```

## ⚡ Оптимизация производительности

### ▶️ Продолжение прерванного экспорта

Автоматически продолжает с последнего `serialNo`:### Проблема

Экспорт большого периода (год) может занимать **1-2 часа** из-за медленного ответа устройства.

```bash

python export_acs_events.py --password CHANGE_ME --end 2025-12-15T23:59:59 --resume### Решение 1: Без изображений (быстрее на 20-40%)

```Уберите флаг `--pic` если изображения не нужны.



## 🚀 Быстрый старт### Решение 2: Увеличить размер страницы (быстрее на 30-50%)

```bash

### Базовый экспорт (без изображений)--page 50  # или --page 100

```

```bash

python tools/export/export_acs_events.py \Попробуйте увеличить размер страницы, если устройство поддерживает.

  --host 192.168.1.101 \

  --user admin \### Решение 3: Разделение на периоды

  --password your_password \Разбейте большой период на несколько меньших и запускайте параллельно:

  --end "2025-12-31T23:59:59" \

  --out data/events.ndjson \```bash

  --verbose# Январь-Июнь

```python tools/export/export_acs_events.py ... --start "2025-01-01" --end "2025-06-30"



### Экспорт с изображениями# Июль-Декабрь

python tools/export/export_acs_events.py ... --start "2025-07-01" --end "2025-12-31"

```bash```

python tools/export/export_acs_events.py \

  --host 192.168.1.101 \## 📊 Параметры

  --user admin \

  --password your_password \### Обязательные

  --end "2025-12-31T23:59:59" \- `--host` - IP адрес устройства

  --pic \- `--user` - Имя пользователя

  --out data/events_with_pic.ndjson \- `--password` - Пароль

  --verbose- `--start` - Дата начала (формат: `YYYY-MM-DDTHH:MM:SS`)

```- `--end` - Дата окончания (формат: `YYYY-MM-DDTHH:MM:SS`)



### Экспорт большого периода (с разделением)### Опциональные

- `--out` - Файл вывода (по умолчанию: `events.ndjson`)

```bash- `--pic` - Включить экспорт изображений (base64)

python tools/export/export_split.py \- `--page` - Размер страницы (по умолчанию: 20, макс: 100)

  --host 192.168.1.101 \- `--verbose` - Подробный вывод

  --user admin \- `--timeout` - Таймаут запроса в секундах (по умолчанию: 30)

  --password your_password \

  --start "2024-01-01" \## 📄 Формат вывода (NDJSON)

  --end "2024-12-31" \

  --chunk-days 30 \Каждая строка - JSON объект события:

  --keep-chunks \

  --out data/events_2024.ndjson```json

```{"major": 5, "minor": 75, "time": "2025-12-01T06:05:04+03:00", "cardNo": "12345", "name": "Employee Sample", "employeeNoString": "55", "serialNo": 97659}

{"major": 5, "minor": 104, "time": "2025-12-01T17:30:15+03:00", "cardNo": "12345", "name": "Employee Sample", "employeeNoString": "55", "serialNo": 97662}

## 📊 Параметры export_acs_events.py```



### Подключение### Коды событий (minor)

| Параметр | По умолчанию | Описание |- **75** - Успешный вход (карта/лицо)

|----------|--------------|----------|- **104** - Успешный выход (карта/лицо)

| `--host` | 192.168.1.101 | IP адрес устройства |- **21** - Дверь открыта

| `--user` | admin | Имя пользователя |- **22** - Дверь закрыта

| `--password` | **обязателен** | Пароль |- **76** - Неопознанное лицо/карта



### Период экспорта## 🔧 Тестирование производительности

| Параметр | По умолчанию | Описание |

|----------|--------------|----------|Для тестирования разных размеров страниц:

| `--start` | 2000-01-01T00:00:00 | Начало периода |

| `--end` | **обязателен** | Конец периода |```bash

python tools/export/test_performance.py \

### Выходной файл  --host 192.168.1.101 \

| Параметр | По умолчанию | Описание |  --user admin \

|----------|--------------|----------|  --password your_password

| `--out` | events.ndjson | Имя выходного файла |```

| `--force` | false | Перезаписать существующий файл |

| `--append` | false | Дополнить существующий файл |Тест проверит размеры страниц: 10, 20, 30, 50, 100.

| `--backup` | false | Создать резервную копию |

## ⚠️ Возможные проблемы

### Дедупликация

| Параметр | По умолчанию | Описание |### 1. Таймаут соединения

|----------|--------------|----------|**Проблема:** Устройство не отвечает.

| `--deduplicate` | false | Включить дедупликацию |**Решение:** Увеличьте `--timeout 60` или проверьте доступность устройства.

| `--resume` | false | Продолжить с последнего serialNo |

### 2. Ошибка 401 Unauthorized

### Изображения**Проблема:** Неверные логин/пароль.

| Параметр | По умолчанию | Описание |**Решение:** Проверьте учётные данные.

|----------|--------------|----------|

| `--pic` | false | Включить picEnable=true |### 3. Медленный экспорт

| `--img-dir` | event_images | Директория для JPEG |**Проблема:** Экспорт занимает слишком много времени.

| `--no-save-images` | false | Не сохранять JPEG |**Решение:** 

- Уберите `--pic` если изображения не нужны

### Сетевые настройки- Увеличьте `--page` до 50-100

| Параметр | По умолчанию | Описание |- Разделите период на части

|----------|--------------|----------|

| `--timeout` | 180 | Таймаут чтения (сек) |### 4. Недопустимый размер страницы

| `--retries` | 5 | Количество повторов |**Проблема:** `Invalid pageSize`.

| `--backoff` | 1.0 | Задержка между повторами |**Решение:** Уменьшите `--page` до 20-30.

| `--page` | 30 | Размер страницы |

## 📚 Дополнительная документация

## 📊 Параметры export_split.py

Полная документация API устройства: `docs/ACT-T1342EW_ISAPI_Full_Documentation.pdf`

### Период и разбиение

| Параметр | По умолчанию | Описание |## 🔗 Использование результатов

|----------|--------------|----------|

| `--start` | **обязателен** | Начальная дата (YYYY-MM-DD) |Экспортированные файлы можно анализировать через LogStorm:

| `--end` | **обязателен** | Конечная дата (YYYY-MM-DD) |

| `--chunk-days` | 30 | Размер периода в днях |```bash

# GUI

### Выходные файлыpython app.py

| Параметр | По умолчанию | Описание |# Выберите NDJSON файл из data/

|----------|--------------|----------|

| `--out` | events_merged.ndjson | Итоговый файл |# CLI

| `--chunks-dir` | chunks | Директория для частей |python cli.py --logs data/events.ndjson --type ndjson

| `--keep-chunks` | false | Сохранить промежуточные файлы |```



### Режим работы---

| Параметр | По умолчанию | Описание |

|----------|--------------|----------|**Версия:** 1.0  

| `--force` | false | Перезаписать существующие файлы |**Дата:** 22.12.2025  

| `--no-deduplicate` | false | Отключить дедупликацию |**Совместимость:** Hikvision/HiWatch СКУД с поддержкой ISAPI

| `--backup` | false | Создать резервную копию |

## ⚡ Оптимизация производительности

### 1. Без изображений (быстрее на 20-40%)
Уберите флаг `--pic` если изображения не нужны.

### 2. Увеличить размер страницы (быстрее на 30-50%)
```bash
--page 50  # или --page 100 (если устройство поддерживает)
```

### 3. Разделение на периоды (параллельный запуск)
Используйте `export_split.py` с `--keep-chunks` и запускайте несколько 
экземпляров для разных периодов.

## 📄 Формат вывода (NDJSON)

Каждая строка - JSON объект события:

```json
{"major": 5, "minor": 75, "time": "2025-12-01T06:05:04+03:00", "serialNo": 97659}
{"major": 5, "minor": 104, "time": "2025-12-01T17:30:15+03:00", "serialNo": 97662}
```

### Коды событий (minor)
| Код | Описание |
|-----|----------|
| 75 | Успешный вход (карта/лицо) |
| 104 | Успешный выход (карта/лицо) |
| 21 | Дверь открыта |
| 22 | Дверь закрыта |
| 76 | Неопознанное лицо/карта |

## 🔄 Примеры использования

### Ежедневный экспорт (cron)

```bash
#!/bin/bash
# Экспорт за вчера с дополнением файла
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d)
TODAY=$(date +%Y-%m-%d)

python export_acs_events.py \
  --password CHANGE_ME \
  --start "${YESTERDAY}T00:00:00" \
  --end "${TODAY}T00:00:00" \
  --out events_${YESTERDAY}.ndjson \
  --deduplicate
```

### Восстановление прерванного экспорта

```bash
# 1. Экспорт был прерван
python export_acs_events.py --password CHANGE_ME --end 2025-12-31T23:59:59 --out events.ndjson
# Ctrl+C

# 2. Продолжение с места остановки
python export_acs_events.py --password CHANGE_ME --end 2025-12-31T23:59:59 \
  --out events.ndjson --resume --append
```

### Миграция с дедупликацией

```bash
# Объединить несколько файлов с удалением дубликатов
python -c "
from export_utils import merge_ndjson_files
merge_ndjson_files(
    ['old1.ndjson', 'old2.ndjson', 'old3.ndjson'],
    'merged.ndjson',
    deduplicate=True
)
"
```

## 🛠️ Утилиты (export_utils.py)

### EventDeduplicator
```python
from export_utils import EventDeduplicator

dedup = EventDeduplicator()
dedup.load_existing_events("events.ndjson")

for event in new_events:
    if not dedup.is_duplicate(event):
        process(event)

dedup.print_stats()
```

### Защита от перезаписи
```python
from export_utils import get_safe_output_path

# Если file.ndjson существует → вернёт file_20251222_143000.ndjson
path = get_safe_output_path("file.ndjson")
```

### Объединение файлов
```python
from export_utils import merge_ndjson_files

total, dups = merge_ndjson_files(
    ["file1.ndjson", "file2.ndjson"],
    "merged.ndjson",
    deduplicate=True
)
```
