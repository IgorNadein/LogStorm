# LogStorm

LogStorm анализирует логи посещаемости сотрудников из CSV, NDJSON и collector SQLite баз событий СКУД Hikvision/HiWatch, нормализует сотрудников через маппинг, отделяет технические сбои от рабочих нарушений и формирует Excel-отчеты.

Текущий приоритет проекта: стабильный core, collector и pytest-покрытие. Разработка GUI приостановлена; код в `gui/` сохранен как экспериментальный слой и не входит в обязательный тестовый контур.

## Текущее состояние

- Core CLI: `main.py`
- Данные для локального smoke/integration прогона: `data/attendance.csv`, `data/vhod.ndjson`, `data/vihod.ndjson`
- Маппинг сотрудников для NDJSON: `person.json`
- Конфигурация по умолчанию: `config/paths.py`, `config/analysis.py`, `config/formatting.py`, `config/localization.py`
- Collector: `collector/collector.py`, `collector/storage.py`
- SQLAlchemy ORM-модели collector storage: `models/collector_event.py`
- Экспорт из устройства: `tools/export/export_acs_events.py`
- GUI: `run_gui.py`, `gui/` (paused/experimental)

## Установка

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

GUI-зависимости могут требовать отдельной настройки окружения. Основной проверяемый контур проекта сейчас не зависит от запуска GUI.

## Проверка

Главный источник правды по текущему поведению проекта - `pytest`.

```bash
python -m pytest
python -m pytest -q -m "not realdb"
python -m pytest -q -m realdb --real-db /home/lizerk/Dev/LogStorm/events.db
python -m compileall -q .
```

Покрываемые слои:

- unit: конфигурация, модели, валидаторы, анализаторы, утилиты;
- public API/core: `DataLoader`, `PersonMapper`, `AttendanceService`, `ExcelReporter`;
- EUSRR service contract: сотрудник, период, внешний график, календарные исключения;
- collector: конфиг, HTTP-клиент, state tracking, NDJSON+SQLite storage;
- SQLAlchemy: чтение collector DB, фильтры по сотруднику, периоду и устройству;
- integration: CSV/NDJSON/SQLite -> анализ -> DTO/Excel во временный файл.

EUSRR считается источником графика, праздников, переносов и особых дней.
LogStorm применяет переданный календарь к событиям коллектора; `employee_id`
из запроса должен совпадать с `employeeNoString` в логах.

## Запуск CLI

```bash
python main.py
```

По умолчанию CLI читает:

- логи: `data/attendance.csv`;
- маппинг: не задан, чтобы CSV sample анализировался без фильтрации;
- отчет: `reports/attendance_report.xlsx`.

Эти значения задаются в `config/paths.py`. Для production-сценариев лучше завести отдельный локальный конфиг или обновлять эти значения через будущий config loader, а не хардкодить пути в бизнес-логике.

## Форматы данных

CSV:

```csv
timestamp,camera,name,distance,identity
2025-10-01T15:59:57,main_entrance,igor_nadein,0.34107,"data\people\igor_nadein\photo.jpg"
```

NDJSON:

```json
{"major": 5, "minor": 75, "time": "2025-12-01T06:05:04+03:00", "name": "Employee Delta", "employeeNoString": "55", "serialNo": 97659}
```

SQLite collector DB:

```python
from services import DataLoader, PersonMapper

mapper = PersonMapper("person.json")
df = DataLoader.load_logs("events.db", file_type="sqlite", person_mapper=mapper)
```

`file_type="auto"` также распознает расширения `.db`, `.sqlite`, `.sqlite3`.

Поддерживаемые события СКУД:

- `minor=75` - успешный вход;
- `minor=104` - успешный выход;
- `minor=21/22` - дверь открыта/закрыта;
- `minor=76` - неопознанное лицо.

## Маппинг сотрудников

`person.json` использует формат:

```json
{
  "person_mappings": {
    "19": {
      "display_name": "Employee Alpha",
      "workdays": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
      "start_time": "08:00",
      "work_hours": 9
    }
  },
  "aliases": {
    "19": ["666"]
  }
}
```

`PersonMapper` умеет:

- менять отображаемые имена;
- применять индивидуальные графики;
- объединять несколько ID одного сотрудника через `aliases`;
- работать как источник профилей для `AttendanceService`.

## Collector

Collector собирает события СКУД и пишет их одновременно в NDJSON и SQLite:

```bash
python collector/collector.py --init
python collector/collector.py --config collector/collector.example.json --once
```

В тестах сетевой доступ не требуется: collector проверяется через конфигурацию, состояние, дедупликацию и локальное хранилище.

## Структура

```text
LogStorm/
├── analyzers/          # анализ статусов и технических сбоев
├── collector/          # сборщик событий и storage
├── config/             # настройки проекта
├── data/               # локальные тестовые/примерные данные
├── gui/                # GUI paused/experimental
├── models/             # AttendanceRecord, WorkSchedule
├── reporters/          # Excel и текстовая сводка
├── services/           # DataLoader, AttendanceService, PersonMapper
├── tests/              # pytest-контур
├── tools/export/       # экспорт событий из устройства
├── utils/              # даты, Excel helpers, исключения, логирование
└── validators/         # проверки отсутствий и времени
```

## Что сейчас не является приоритетом

- GUI не считается основным пользовательским путем.
- AI-интеграция удалена из текущего кода и документации.
- Старые пути `LogsCam/`, `path/person_prefs.json`, `gui_app.py`, `gui_config.py`, `gui_app_fluent.py`, `config.py` не являются актуальной структурой.
