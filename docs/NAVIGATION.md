# Навигация по LogStorm

## Основные команды

```bash
python -m pytest
python -m compileall -q .
python main.py --help
python main.py analyze
python main.py api --db-path /home/lizerk/Dev/LogStorm/events.db
python main.py collector --once
```

## Главные файлы

| Файл | Назначение |
| --- | --- |
| `main.py` | Универсальная management-точка входа: analyze, api, collector, check, mapping |
| `core/settings.py` | Единый Python settings module |
| `data/person.sample.json` | Sample mapping сотрудников и aliases |
| `collector/collector.py` | Сборщик событий СКУД |
| `collector/storage.py` | NDJSON + SQLite хранилище |
| `core/models/collector.py` | SQLAlchemy ORM-модели collector DB |
| `core/repositories/collector_events.py` | Repository для чтения collector DB |
| `api/app.py` | FastAPI app factory и маршруты |
| `api/schemas.py` | Pydantic DTO HTTP API |
| `api/auth.py` | Auth dependency для HTTP API |
| `tools/export/export_acs_events.py` | Ручной экспорт событий из устройства |
| `tools/check_environment.py` | Проверка локального окружения |

## Папки

| Папка | Содержимое |
| --- | --- |
| `analyzer/` | `DataLoader`, `AttendanceService`, EUSRR contract, статусы, валидаторы, отчеты |
| `core/` | Settings, shared models, repositories |
| `api/` | FastAPI transport |
| `collector/` | Фоновый сбор событий и storage |
| `data/` | Локальные CSV/NDJSON данные для проверок |
| `tests/` | Pytest-проверки всех активных слоев |

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
- GUI: удален из active scope.
- AI: удален из текущего проекта.
