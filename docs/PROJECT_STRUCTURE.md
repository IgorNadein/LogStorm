# Структура проекта LogStorm

## Активный контур

```text
LogStorm/
├── main.py
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

- `main.py` - CLI запуск анализа по дефолтным путям из `config/paths.py`.
- `collector/collector.py` - фоновый или однократный сбор событий СКУД.
- `tools/export/export_acs_events.py` - ручной экспорт событий из устройства.
- `run_gui.py` - GUI entrypoint, сейчас не является частью основного тестового контура.

## Конфигурация

- `config/paths.py` - `data/attendance.csv`, optional mapping path, `reports/attendance_report.xlsx`.
- `config/analysis.py` - рабочий график и пороги анализа.
- `config/formatting.py` - Excel-цвета и имена листов.
- `config/localization.py` - локализация дней и месяцев.
- `config.json` - пользовательские GUI-настройки, не источник истины для core CLI.

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
