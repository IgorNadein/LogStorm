# Структура проекта LogStorm

## Активный контур

```text
LogStorm/
├── main.py
├── analyzer/
├── core/
├── config/
├── services/
├── analyzers/
├── validators/
├── models/
├── reporters/
├── collector/
├── tools/export/
├── data/
├── tests/
└── utils/
```

## Точки входа

- `main.py` - CLI запуск анализа по дефолтным путям из `core/settings.py`.
- `collector/collector.py` - фоновый или однократный сбор событий СКУД.
- `tools/export/export_acs_events.py` - ручной экспорт событий из устройства.
- `run_gui.py` - GUI entrypoint, сейчас не является частью основного тестового контура.

## Конфигурация

- `core/settings.py` - единый Python settings module для API, CLI, collector и analyzer.
- `config/*` - legacy/default compatibility layer, постепенно выводится из активного контура.
- `config/formatting.py` - Excel-цвета и имена листов.
- `config/localization.py` - локализация дней и месяцев.
- `config.json` - локальные пользовательские GUI-настройки, не хранится в Git и не является источником истины для core CLI/API/collector.

## Активные приложения

- `core/` - общие настройки, модели и repositories.
- `analyzer/` - бизнес-логика посещаемости.
- `collector/` - сбор событий и запись в NDJSON/SQLite.
- `api/` - FastAPI transport.
- `gui/` - paused/experimental.

`services/`, `analyzers/`, `validators/`, `reporters/`, `models/` оставлены как compatibility wrappers для старых импортов.

## Данные

- `data/attendance.csv` - CSV fixture/sample.
- `data/vhod.ndjson` и `data/vihod.ndjson` - NDJSON fixture/sample.
- `person.json` - текущий маппинг сотрудников.
- `events.db` - поддерживаемый collector SQLite формат, читается через SQLAlchemy при наличии файла.

## Тесты

`pytest` проверяет:

- конфигурацию и совместимые константы;
- модели и рабочий график;
- маппинг сотрудников и aliases;
- CSV/NDJSON загрузку;
- SQLite collector DB загрузку через SQLAlchemy;
- полный core pipeline;
- Excel export во временную папку;
- collector config/state/storage;
- утилиты и исключения.

## Отложенный код

`gui/` и `run_gui.py` сохранены, но разработка GUI приостановлена. При изменениях core не нужно считать GUI smoke-import обязательным, пока решение по GUI не принято.

## Устаревшие имена, которых не должно быть в новой документации

- `LogsCam/`;
- `path/person_prefs.json`;
- `gui_app.py`;
- `gui_config.py`;
- `gui_app_fluent.py`;
- корневой `config.py`;
- `person_mapping.json` как основной файл маппинга.
