# LogStorm Collector

Автономный сборщик событий СКУД с камер Hikvision/HiWatch.

## Быстрый старт

```bash
# 1. Создать конфигурацию
python collector.py --init

# 2. Отредактировать collector.json (указать камеры, пути)

# 3. Тестовый запуск (однократный сбор)
python collector.py --once --verbose

# 4. Запуск в режиме демона (каждые N минут)
python collector.py
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
WorkingDirectory=/path/to/LogStorm/collector
ExecStart=/usr/bin/python3 /path/to/LogStorm/collector/collector.py
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
