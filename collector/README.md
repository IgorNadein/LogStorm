# LogStorm Collector

Автономный сборщик событий СКУД с камер Hikvision/HiWatch.

## Быстрый старт

```bash
# 1. Настроить .env (БД, камеры, пути)

# 2. Тестовый запуск (однократный сбор)
python collector.py --once --verbose

# 3. Запуск в режиме демона (каждые N минут)
python collector.py
```

`collector.local.py` больше не обязателен. Если файла нет, collector использует
настройки из `.env` / `core.settings`. Если файл есть, он работает как legacy
override поверх базового env-конфига.

## Догрузка фотографий для старых событий

Если камера уже начала отдавать фото, а коллектор в тот период работал без
`images.enabled`, можно выполнить разовый backfill по SQLite:

```bash
# Проверить старые события без _imagePath и попробовать догрузить фото
python collector.py --backfill-images --verbose

# Ограничить количество проверяемых событий
# Для backfill берутся самые новые события без фото
python collector.py --backfill-images --backfill-limit 500 --verbose
```

Что делает backfill:
- читает события из SQLite без `_imagePath`
- группирует их по устройствам и идёт по камере страницами так же, как обычная
  синхронизация
- в каждом ответе сопоставляет события по `eventID` (если есть) или `serialNo`
- сохраняет найденные фото в папку `images.folder`
- обновляет только `_imagePath` в `event_data` SQLite

Ограничение:
- NDJSON не переписывается, backfill обновляет только SQLite
- если потом пересобрать SQLite из NDJSON, пути к догруженным фото нужно будет
  восстановить повторным backfill

## Миграция relational storage в PostgreSQL

Collector storage уже работает через SQLAlchemy, поэтому перенос можно делать
отдельной management-командой:

```bash
python main.py collector-migrate \
  --source-db /path/to/events.db
```

Куда мигрировать, команда берёт из настроек проекта:
- `LOGSTORM_COLLECTOR_DB_URL` в `.env` или окружении
- либо старый ключ совместимости `LOGSTORM_COLLECTOR_DB_PATH`

Например:

```bash
export LOGSTORM_COLLECTOR_DB_URL=postgresql+psycopg://user:pass@localhost/logstorm
python main.py collector-migrate --source-db /path/to/events.db
```

По умолчанию команда отказывается писать в непустой target. Если переносишь в уже
подготовленную тестовую базу и хочешь заменить содержимое, укажи `--overwrite`.

`--target-db` остаётся как явный override для разовых случаев.

Для подробного прогресса по пакетам:

```bash
python main.py collector-migrate \
  --source-db /path/to/events.db \
  --overwrite \
  --verbose
```

## Развёртывание

### Linux (systemd)

Создать `/etc/systemd/system/logstorm-collector.service`:

```ini
[Unit]
Description=LogStorm Event Collector
After=network.target

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/path/to/LogStorm
EnvironmentFile=/path/to/LogStorm/.env
ExecStart=/path/to/LogStorm/.venv/bin/python /path/to/LogStorm/main.py collector --verbose
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Запуск:
```bash
sudo systemctl daemon-reload
sudo systemctl enable logstorm-collector
sudo systemctl start logstorm-collector
```

### Windows (планировщик задач)

Создать задачу:
- Триггер: При запуске системы
- Действие: `python C:\LogStorm\collector\collector.py`
- Настройки: Перезапускать при сбое

## Утилиты

- `rebuild_sqlite.py` — Восстановить SQLite из NDJSON
- `show_state.py` — Показать состояние коллектора
- `check_events.py` — Проверка последних событий
- `check_fresh.py` — Проверка событий за 5 минут
- `verify_all.py` — Полная проверка камер

## Документация

- [README_STORAGE.md](README_STORAGE.md) — Архитектура хранилища
- [MIGRATION_SQLITE.md](MIGRATION_SQLITE.md) — Миграция на SQLite
