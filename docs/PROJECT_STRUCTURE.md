# Структура проекта LogStorm

## Активный контур

```text
LogStorm/
├── main.py
├── api/
├── analyzer/
├── core/
├── collector/
├── tools/export/
├── data/
├── tests/
└── utils/
```

## Точки входа

- `main.py` - management entrypoint для `analyze`, `api`, `collector`, `check`, `mapping`.
- `collector/collector.py` - реализация фонового или однократного сбора событий СКУД.
- `tools/export/export_acs_events.py` - ручной экспорт событий из устройства.

## Конфигурация

- `core/settings.py` - единый Python settings module для API, CLI, collector и analyzer.

## Активные приложения

- `core/` - общие настройки, модели и repositories.
- `analyzer/` - бизнес-логика посещаемости.
- `collector/` - сбор событий и запись в NDJSON/SQLite.
- `api/` - FastAPI transport.

## Данные

- `data/attendance.csv` - CSV fixture/sample.
- `data/vhod.ndjson` и `data/vihod.ndjson` - NDJSON fixture/sample.
- `data/person.sample.json` - sample mapping сотрудников.
- `events.db` - поддерживаемый collector SQLite формат, читается через SQLAlchemy при наличии файла.

## Тесты

`pytest` проверяет:

- runtime settings и константы проекта;
- модели и рабочий график;
- маппинг сотрудников и aliases;
- CSV/NDJSON загрузку;
- SQLite collector DB загрузку через SQLAlchemy;
- полный core pipeline;
- Excel export во временную папку;
- collector config/state/storage;
- утилиты и исключения.

## Удаленный GUI

GUI больше не входит в active scope проекта. Старые `gui/`, `run_gui.py` и
`tools/app.py` удалены; основные сценарии выполняются через `main.py`, API и
collector.

## Устаревшие имена, которых не должно быть в новой документации

- `LogsCam/`;
- `path/person_prefs.json`;
- `run_gui.py`;
- `gui/`;
- `gui_app.py`;
- `gui_config.py`;
- `gui_app_fluent.py`;
- `config.json`;
- корневой `config.py`;
- `person_mapping.json` как основной файл маппинга.
