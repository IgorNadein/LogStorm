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
| `core/settings.py` | Единый Python settings module |
| `person.json` | Маппинг сотрудников и aliases |
| `collector/collector.py` | Сборщик событий СКУД |
| `collector/storage.py` | NDJSON + SQLite хранилище |
| `core/models/collector.py` | SQLAlchemy ORM-модели collector DB |
| `core/repositories/collector_events.py` | Repository для чтения collector DB |
| `api/app.py` | FastAPI app factory и маршруты |
| `api/schemas.py` | Pydantic DTO HTTP API |
| `api/auth.py` | Auth dependency для HTTP API |
| `tools/export/export_acs_events.py` | Ручной экспорт событий из устройства |
| `run_gui.py` | GUI entrypoint, сейчас paused/experimental |

## Папки

| Папка | Содержимое |
| --- | --- |
| `analyzer/` | `DataLoader`, `AttendanceService`, EUSRR contract, статусы, валидаторы, отчеты |
| `core/` | Settings, shared models, repositories |
| `services/`, `analyzers/`, `validators/`, `reporters/`, `models/` | Compatibility wrappers |
| `collector/` | Фоновый сбор событий и storage |
| `data/` | Локальные CSV/NDJSON данные для проверок |
| `tests/` | Pytest-проверки всех активных слоев |
| `gui/` | Отложенный GUI слой |

## Где смотреть

| Задача | Файл |
| --- | --- |
| Настроить runtime | `core/settings.py` |
| Проверить CSV/NDJSON загрузку | `analyzer/data_loader.py` |
| Проверить маппинг сотрудников | `analyzer/person_mapper.py` |
| Проверить анализ посещаемости | `analyzer/service.py` |
| Проверить collector storage | `collector/storage.py` |
| Проверить collector API | `collector/collector.py` |
| Проверить SQLite чтение анализатором | `core/repositories/collector_events.py` + `analyzer/data_loader.py` |
| Обновить тестовые ожидания | `tests/` |

## Статусы

- Core CLI: активен.
- Collector: активен.
- Public API/core services: активны.
- GUI: paused/experimental.
- AI: удален из текущего проекта.
