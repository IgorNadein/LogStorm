**Язык:** [English](README.md) | [Русский](README.ru.md) | [Deutsch](README.de.md) | [Español](README.es.md)

# LogStorm

LogStorm - backend/data-processing система для логов событий СКУД. Проект читает CSV, NDJSON и collector SQLite источники событий Hikvision/HiWatch-style систем контроля доступа, нормализует сотрудников через правила маппинга, отделяет технические сбои от рабочих нарушений и формирует Excel-отчеты.

Текущий приоритет проекта: стабильный core, collector, HTTP API и pytest-покрытие. GUI удален из активного scope; основной путь работы идет через `main.py`.

Публичный репозиторий содержит только синтетические demo-данные. Реальные логи доступа, credentials, сгенерированные отчеты и приватные mapping-файлы должны оставаться вне Git.

## Текущее состояние

- Core CLI: `main.py`
- Данные для локального smoke/integration прогона: `data/attendance.csv`, `data/vhod.ndjson`, `data/vihod.ndjson`
- Пример маппинга сотрудников для NDJSON: `data/person.sample.json`
- Runtime core: `core/settings.py` объединяет настройки API, CLI, collector и analyzer.
- Analyzer app: `analyzer/` содержит загрузку данных, маппинг, анализ, валидаторы и отчеты.
- Collector: `collector/collector.py`, `collector/storage.py`
- Shared models/repositories: `core/models/`, `core/repositories/`
- Экспорт из устройства: `tools/export/export_acs_events.py`

## Установка

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Проверить локальное окружение можно командой:

```bash
python tools/check_environment.py
```

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
- collector: конфиг, HTTP-клиент, state tracking, NDJSON и SQLite storage;
- SQLAlchemy: чтение collector DB, фильтры по сотруднику, периоду и устройству;
- integration: CSV/NDJSON/SQLite -> анализ -> DTO/Excel во временный файл.

EUSRR считается источником графика, праздников, переносов и особых дней. LogStorm применяет переданный календарь к событиям коллектора; `employee_id` из запроса должен совпадать с `employeeNoString` в логах или быть связан с ним через request-level `aliases`.

## Management CLI

```bash
python main.py --help
python main.py analyze
python main.py api --db-path /home/lizerk/Dev/LogStorm/events.db
python main.py collector --once
python main.py check
```

`python main.py` без подкоманды сохраняет прежнее поведение и запускает `analyze`. По умолчанию анализ читает:

- логи: `data/attendance.csv`;
- маппинг: не задан, чтобы CSV sample анализировался без фильтрации;
- отчет: `reports/attendance_report.xlsx`.

Эти значения задаются в `core/settings.py` и читаются через `LogStormCore`.

## Runtime Core

Активные entrypoint должны получать настройки через `core.LogStormCore`. Это текущая точка объединения источников истины:

- `core/settings.py` устроен как простой Django-style settings module;
- настройки анализа, путей, форматирования и локализации лежат в одном `core/settings.py`;
- переменные `LOGSTORM_*` переопределяют runtime-настройки API;
- `LogStormCore` передает согласованный runtime context в API/CLI.

Пример:

```python
from core import LogStormCore, build_settings

settings = build_settings()
core = LogStormCore(settings)
db_path = core.settings.api.collector_db_path
default_schedule = core.default_schedule_payload()
```

## Форматы данных

CSV:

```csv
timestamp,camera,name,distance,identity
2026-04-20T08:54:00,main_entrance,employee_alpha,0.34107,"data/people/employee_alpha/photo.jpg"
```

NDJSON:

```json
{"major": 5, "minor": 75, "time": "2026-04-20T08:54:00+03:00", "name": "Employee Alpha", "employeeNoString": "19", "serialNo": "SAMPLE-ENTRY-001"}
```

SQLite collector DB:

```python
from analyzer import DataLoader, PersonMapper

mapper = PersonMapper("data/person.sample.json")
df = DataLoader.load_logs("events.db", file_type="sqlite", person_mapper=mapper)
```

## HTTP API

LogStorm может отдавать анализ посещаемости через HTTP:

```bash
LOGSTORM_COLLECTOR_DB_PATH=/path/to/events.db \
LOGSTORM_API_TOKEN=change-me \
uvicorn api.app:app --host 0.0.0.0 --port 8000
```

`api.app` читает эти значения через `LogStormCore`.

Endpoint:

- `GET /health`
- `POST /attendance/analyze`

`POST /attendance/analyze` принимает опциональный `aliases: string[]`. События, где `employeeNoString` совпадает с одним из aliases, объединяются в canonical `employee_id` для текущего ответа анализа.

`LOGSTORM_API_TOKEN` опционален для локальной разработки. Если он задан, клиенты должны отправлять `Authorization: Bearer <token>`.

Если EUSRR не отправляет `schedule`, LogStorm использует дефолтный график из `core/settings.py`. Fallback управляется переменными:

- `LOGSTORM_ALLOW_DEFAULT_SCHEDULE=false` - отклонять запросы без `schedule`;
- `LOGSTORM_DEFAULT_START_TIME=08:00`;
- `LOGSTORM_DEFAULT_END_TIME=17:00`;
- `LOGSTORM_DEFAULT_EXPECTED_HOURS=9`;
- `LOGSTORM_DEFAULT_WORKDAYS=Monday,Tuesday,Wednesday,Thursday,Friday`.

`file_type="auto"` также распознает расширения `.db`, `.sqlite`, `.sqlite3`.

Поддерживаемые события СКУД:

- `minor=75` - успешный вход;
- `minor=104` - успешный выход;
- `minor=21/22` - дверь открыта/закрыта;
- `minor=76` - неопознанное лицо.

## Маппинг сотрудников

Sample mapping `data/person.sample.json` использует формат:

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
python main.py collector --once
python main.py collector --config collector/collector.local.py --once  # legacy override
```

В тестах сетевой доступ не требуется: collector проверяется через конфигурацию, состояние, дедупликацию и локальное хранилище.

По умолчанию collector берет конфиг из `.env` / `core.settings`. `collector.local.py` остается только как необязательный legacy override с верхнеуровневым словарем `CONFIG`. JSON-конфиги читаются только для обратной совместимости.

## Структура

Подробное описание архитектурных границ: `docs/ARCHITECTURE.md`.

```text
LogStorm/
├── analyzer/           # анализ посещаемости, загрузчики, валидаторы, отчеты
├── api/                # FastAPI слой
├── collector/          # сборщик событий и storage
├── core/               # настройки, общие модели и repositories
├── data/               # локальные тестовые/demo-данные
├── tests/              # pytest-контур
├── tools/export/       # экспорт событий из устройства
└── utils/              # даты, Excel helpers, исключения, логирование
```

## Вне активного scope

- GUI удален из active scope.
- AI-интеграция удалена из текущего кода и документации.
- Старые пути `LogsCam/`, `path/person_prefs.json`, `run_gui.py`, `gui/`, `gui_app.py`, `gui_config.py`, `gui_app_fluent.py`, `config.json`, `config.py` не являются актуальной структурой.
