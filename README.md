**Language:** [English](README.md) | [Русский](README.ru.md) | [Deutsch](README.de.md) | [Español](README.es.md)

# LogStorm

LogStorm is a backend/data-processing system for access-control event logs. It reads CSV, NDJSON, and collector SQLite event sources from Hikvision/HiWatch-style access-control systems, normalizes employee identifiers through mapping rules, separates technical failures from employee-related attendance cases, and generates Excel reports.

The current project focus is a stable core, collector, HTTP API, and pytest coverage. The GUI was removed from the active scope; the main workflow now goes through `main.py`.

The public repository contains synthetic demo data only. Real access logs, credentials, generated reports, and private mappings must stay outside Git.

## Current State

- Core CLI: `main.py`
- Local smoke/integration sample data: `data/attendance.csv`, `data/vhod.ndjson`, `data/vihod.ndjson`
- NDJSON employee mapping example: `data/person.sample.json`
- Runtime core: `core/settings.py` combines API, CLI, collector, and analyzer settings.
- Analyzer app: `analyzer/` contains data loading, mapping, analysis, validators, and reports.
- Collector: `collector/collector.py`, `collector/storage.py`
- Shared models/repositories: `core/models/`, `core/repositories/`
- Device export tool: `tools/export/export_acs_events.py`

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Check the local environment:

```bash
python tools/check_environment.py
```

## Verification

The main source of truth for current behavior is `pytest`.

```bash
python -m pytest
python -m pytest -q -m "not realdb"
python -m pytest -q -m realdb --real-db /home/lizerk/Dev/LogStorm/events.db
python -m compileall -q .
```

Covered layers:

- unit: configuration, models, validators, analyzers, utilities;
- public API/core: `DataLoader`, `PersonMapper`, `AttendanceService`, `ExcelReporter`;
- EUSRR service contract: employee, period, external schedule, calendar exceptions;
- collector: configuration, HTTP client, state tracking, NDJSON and SQLite storage;
- SQLAlchemy: collector DB reads, employee filters, period filters, device filters;
- integration: CSV/NDJSON/SQLite -> analysis -> DTO/Excel output.

EUSRR is treated as the source of schedules, holidays, transferred working days, and special days. LogStorm applies the supplied calendar to collector events. Request `employee_id` must match `employeeNoString` in the logs or be connected through request-level `aliases`.

## Management CLI

```bash
python main.py --help
python main.py analyze
python main.py api --db-path /home/lizerk/Dev/LogStorm/events.db
python main.py collector --once
python main.py check
```

Running `python main.py` without a subcommand keeps the historical behavior and starts `analyze`. By default, analysis reads:

- logs: `data/attendance.csv`;
- mapping: not set, so the CSV sample is analyzed without filtering;
- report: `reports/attendance_report.xlsx`.

These values are defined in `core/settings.py` and read through `LogStormCore`.

## Runtime Core

Active entrypoints should receive settings through `core.LogStormCore`. This is the current point where runtime sources of truth are combined:

- `core/settings.py` works as a simple Django-style settings module;
- analysis, path, formatting, and localization settings live in one `core/settings.py`;
- `LOGSTORM_*` environment variables override API runtime settings;
- `LogStormCore` passes a consistent runtime context to the API and CLI.

Example:

```python
from core import LogStormCore, build_settings

settings = build_settings()
core = LogStormCore(settings)
db_path = core.settings.api.collector_db_path
default_schedule = core.default_schedule_payload()
```

## Data Formats

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

LogStorm can expose the attendance analyzer over HTTP:

```bash
LOGSTORM_COLLECTOR_DB_PATH=/path/to/events.db \
LOGSTORM_API_TOKEN=change-me \
uvicorn api.app:app --host 0.0.0.0 --port 8000
```

`api.app` reads these values through `LogStormCore`.

Endpoints:

- `GET /health`
- `POST /attendance/analyze`

`POST /attendance/analyze` accepts optional `aliases: string[]`. Events whose `employeeNoString` matches one of these aliases are merged into the canonical `employee_id` for the current analysis response.

`LOGSTORM_API_TOKEN` is optional for local development. If set, clients must send `Authorization: Bearer <token>`.

If EUSRR does not send `schedule`, LogStorm uses the default schedule from `core/settings.py`. The fallback can be controlled with:

- `LOGSTORM_ALLOW_DEFAULT_SCHEDULE=false` - reject requests without `schedule`;
- `LOGSTORM_DEFAULT_START_TIME=08:00`;
- `LOGSTORM_DEFAULT_END_TIME=17:00`;
- `LOGSTORM_DEFAULT_EXPECTED_HOURS=9`;
- `LOGSTORM_DEFAULT_WORKDAYS=Monday,Tuesday,Wednesday,Thursday,Friday`.

`file_type="auto"` also recognizes `.db`, `.sqlite`, and `.sqlite3` files.

Supported access-control events:

- `minor=75` - successful entry;
- `minor=104` - successful exit;
- `minor=21/22` - door opened/closed;
- `minor=76` - unknown face.

## Employee Mapping

Sample mapping `data/person.sample.json` uses this format:

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

`PersonMapper` can:

- change display names;
- apply individual schedules;
- merge multiple IDs of the same employee through `aliases`;
- work as a profile source for `AttendanceService`.

## Collector

The collector gathers access-control events and writes them to NDJSON and SQLite:

```bash
python main.py collector --once
python main.py collector --config collector/collector.local.py --once  # legacy override
```

Network access is not required in tests: collector behavior is verified through configuration, state tracking, deduplication, and local storage.

By default, the collector reads configuration from `.env` / `core.settings`. `collector.local.py` remains only as an optional legacy override with a top-level `CONFIG` dictionary. JSON configs are read only for backward compatibility.

## Structure

Detailed architecture boundaries: `docs/ARCHITECTURE.md`.

```text
LogStorm/
├── analyzer/           # attendance analysis, loaders, validators, reports
├── api/                # FastAPI layer
├── collector/          # event collector and storage
├── core/               # settings, shared models, repositories
├── data/               # local test/demo data
├── tests/              # pytest suite
├── tools/export/       # device event export
└── utils/              # dates, Excel helpers, exceptions, logging
```

## Out Of Active Scope

- GUI is removed from the active scope.
- AI integration is removed from the current code and documentation.
- Old paths such as `LogsCam/`, `path/person_prefs.json`, `run_gui.py`, `gui/`, `gui_app.py`, `gui_config.py`, `gui_app_fluent.py`, `config.json`, and `config.py` are not part of the current structure.
