# Навигация по LogStorm

## Основные команды

```bash
python -m pytest
python -m compileall -q .
python main.py
```

## Главные файлы

| Файл | Назначение |
| --- | --- |
| `main.py` | CLI smoke/integration запуск core анализа |
| `config/paths.py` | Дефолтные пути к данным, маппингу и отчету |
| `person.json` | Маппинг сотрудников и aliases |
| `collector/collector.py` | Сборщик событий СКУД |
| `collector/storage.py` | NDJSON + SQLite хранилище |
| `models/collector_event.py` | SQLAlchemy ORM-модели collector DB |
| `services/collector_event_repository.py` | Repository для чтения collector DB |
| `tools/export/export_acs_events.py` | Ручной экспорт событий из устройства |
| `run_gui.py` | GUI entrypoint, сейчас paused/experimental |

## Папки

| Папка | Содержимое |
| --- | --- |
| `services/` | `DataLoader`, `AttendanceService`, `PersonMapper`, repository/index |
| `analyzers/` | Статусы и технические сбои |
| `validators/` | Массовые отсутствия и проверки времени |
| `reporters/` | Excel-отчет и консольная сводка |
| `models/` | `AttendanceRecord`, `WorkSchedule` |
| `collector/` | Фоновый сбор событий и storage |
| `data/` | Локальные CSV/NDJSON данные для проверок |
| `tests/` | Pytest-проверки всех активных слоев |
| `gui/` | Отложенный GUI слой |

## Где смотреть

| Задача | Файл |
| --- | --- |
| Настроить дефолтные пути | `config/paths.py` |
| Настроить пороги анализа | `config/analysis.py` |
| Проверить CSV/NDJSON загрузку | `services/data_loader.py` |
| Проверить маппинг сотрудников | `services/person_mapper.py` |
| Проверить анализ посещаемости | `services/attendance_service.py` |
| Проверить collector storage | `collector/storage.py` |
| Проверить collector API | `collector/collector.py` |
| Проверить SQLite чтение анализатором | `services/collector_event_repository.py` + `services/data_loader.py` |
| Обновить тестовые ожидания | `tests/` |

## Статусы

- Core CLI: активен.
- Collector: активен.
- Public API/core services: активны.
- GUI: paused/experimental.
- AI: удален из текущего проекта.
