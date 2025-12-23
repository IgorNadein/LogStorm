# 📥 Экспорт событий СКУД Hikvision/HiWatch

Единый скрипт для экспорта событий доступа через ISAPI в формат NDJSON.

## 🚀 Быстрый старт

```bash
# Базовый экспорт
python tools/export/export_acs_events.py \
  --password your_password \
  --end 2025-12-31T23:59:59

# Экспорт за год с разбиением по месяцам
python tools/export/export_acs_events.py \
  --password your_password \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --chunk-days 30
```

## 🛡️ Ключевые функции

### Защита от перезаписи
По умолчанию файлы **НЕ перезаписываются**:
```bash
# Файл существует → создастся events_20251222_143000.ndjson
python export_acs_events.py --password CHANGE_ME --end 2025-12-31T23:59:59

# Принудительная перезапись
python export_acs_events.py --password CHANGE_ME --end 2025-12-31T23:59:59 --force
```

### Дедупликация
```bash
# Включить фильтрацию дубликатов
python export_acs_events.py --password CHANGE_ME --end 2025-12-31T23:59:59 --deduplicate

# Дополнение файла (авто-дедупликация)
python export_acs_events.py --password CHANGE_ME --end 2025-12-31T23:59:59 --append
```

### Продолжение прерванного экспорта
```bash
python export_acs_events.py --password CHANGE_ME --end 2025-12-31T23:59:59 --resume
```

### Разбиение на периоды
```bash
# Экспорт за год частями по 30 дней
python export_acs_events.py \
  --password CHANGE_ME \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --chunk-days 30
```

## 📊 Все параметры

| Параметр | По умолчанию | Описание |
|----------|--------------|----------|
| **Подключение** | | |
| `--host` | 192.168.1.101 | IP устройства |
| `--user` | admin | Пользователь |
| `--password` | *обязателен* | Пароль |
| **Период** | | |
| `--start` | 2000-01-01 | Начало периода |
| `--end` | *обязателен* | Конец периода |
| `--chunk-days` | 0 | Разбить на части по N дней |
| **Файл** | | |
| `--out` | events.ndjson | Выходной файл |
| `--force` | false | Перезаписать |
| `--append` | false | Дополнить |
| `--backup` | false | Резервная копия |
| **Дедупликация** | | |
| `--deduplicate` | false | Фильтр дубликатов |
| `--resume` | false | Продолжить экспорт |
| **Запрос** | | |
| `--page` | 30 | Размер страницы |
| `--major` | 5 | Major event type |
| `--minor` | 0 | Minor (0=все) |
| **Изображения** | | |
| `--pic` | false | Экспорт фото |
| `--img-dir` | event_images | Папка для фото |
| **Сеть** | | |
| `--timeout` | 180 | Таймаут (сек) |
| `--retries` | 5 | Повторы |

## 📄 Формат вывода

```json
{"major": 5, "minor": 75, "time": "2025-12-01T06:05:04+03:00", "serialNo": 97659, "name": "Employee Sample"}
{"major": 5, "minor": 104, "time": "2025-12-01T17:30:15+03:00", "serialNo": 97662, "name": "Employee Sample"}
```

### Коды событий
| minor | Описание |
|-------|----------|
| 75 | Вход (лицо/карта) |
| 104 | Выход |
| 76 | Неопознанный |

## 💡 Примеры

### Ежедневный экспорт (cron)
```bash
#!/bin/bash
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d)
python export_acs_events.py \
  --password CHANGE_ME \
  --start "${YESTERDAY}T00:00:00" \
  --end "${YESTERDAY}T23:59:59" \
  --out "events_${YESTERDAY}.ndjson"
```

### Восстановление после сбоя
```bash
# Экспорт прерван...
# Продолжить с места остановки:
python export_acs_events.py --password CHANGE_ME --end 2025-12-31T23:59:59 \
  --out events.ndjson --resume --append
```
