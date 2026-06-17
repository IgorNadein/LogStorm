**Sprache:** [English](README.md) | [Русский](README.ru.md) | [Deutsch](README.de.md) | [Español](README.es.md)

# LogStorm

LogStorm ist ein Backend- und Datenverarbeitungssystem für Ereignisprotokolle aus Zutrittskontrollsystemen. Das Projekt liest CSV-, NDJSON- und collector-SQLite-Quellen von Hikvision/HiWatch-ähnlichen Systemen, normalisiert Mitarbeiterkennungen über Mapping-Regeln, trennt technische Störungen von mitarbeiterbezogenen Anwesenheitsfällen und erzeugt Excel-Berichte.

Der aktuelle Schwerpunkt liegt auf einem stabilen Core, Collector, HTTP API und pytest-Abdeckung. Die GUI wurde aus dem aktiven Umfang entfernt; der Hauptworkflow läuft über `main.py`.

Das öffentliche Repository enthält nur synthetische Demo-Daten. Reale Zutrittslogs, Zugangsdaten, generierte Berichte und private Mapping-Dateien dürfen nicht in Git gespeichert werden.

## Aktueller Stand

- Core CLI: `main.py`
- Lokale Smoke-/Integration-Beispieldaten: `data/attendance.csv`, `data/vhod.ndjson`, `data/vihod.ndjson`
- Beispiel für NDJSON-Mitarbeitermapping: `data/person.sample.json`
- Runtime Core: `core/settings.py` bündelt API-, CLI-, Collector- und Analyzer-Einstellungen.
- Analyzer App: `analyzer/` enthält Datenladen, Mapping, Analyse, Validatoren und Berichte.
- Collector: `collector/collector.py`, `collector/storage.py`
- Gemeinsame Modelle/Repositories: `core/models/`, `core/repositories/`
- Geräteexport: `tools/export/export_acs_events.py`

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Lokale Umgebung prüfen:

```bash
python tools/check_environment.py
```

## Verifikation

Die wichtigste Quelle für das aktuelle Verhalten ist `pytest`.

```bash
python -m pytest
python -m pytest -q -m "not realdb"
python -m pytest -q -m realdb --real-db /home/lizerk/Dev/LogStorm/events.db
python -m compileall -q .
```

Abgedeckte Schichten:

- unit: Konfiguration, Modelle, Validatoren, Analyzer, Utilities;
- public API/core: `DataLoader`, `PersonMapper`, `AttendanceService`, `ExcelReporter`;
- EUSRR Service Contract: Mitarbeiter, Zeitraum, externer Zeitplan, Kalenderausnahmen;
- collector: Konfiguration, HTTP-Client, State Tracking, NDJSON- und SQLite-Speicherung;
- SQLAlchemy: Lesen der collector DB, Filter nach Mitarbeiter, Zeitraum und Gerät;
- integration: CSV/NDJSON/SQLite -> Analyse -> DTO/Excel-Ausgabe.

EUSRR gilt als Quelle für Arbeitspläne, Feiertage, verschobene Arbeitstage und Sondertage. LogStorm wendet den übergebenen Kalender auf Collector-Ereignisse an. Die `employee_id` aus der Anfrage muss mit `employeeNoString` in den Logs übereinstimmen oder über request-level `aliases` verbunden sein.

## Management CLI

```bash
python main.py --help
python main.py analyze
python main.py api --db-path /home/lizerk/Dev/LogStorm/events.db
python main.py collector --once
python main.py check
```

`python main.py` ohne Unterbefehl behält das historische Verhalten bei und startet `analyze`. Standardmäßig liest die Analyse:

- Logs: `data/attendance.csv`;
- Mapping: nicht gesetzt, damit das CSV-Sample ohne Filterung analysiert wird;
- Bericht: `reports/attendance_report.xlsx`.

Diese Werte sind in `core/settings.py` definiert und werden über `LogStormCore` gelesen.

## Runtime Core

Aktive Entry Points sollten Einstellungen über `core.LogStormCore` erhalten. Das ist der aktuelle Ort, an dem Runtime-Quellen zusammengeführt werden:

- `core/settings.py` funktioniert als einfaches Django-style settings module;
- Analyse-, Pfad-, Formatierungs- und Lokalisierungseinstellungen liegen in einer Datei `core/settings.py`;
- Umgebungsvariablen `LOGSTORM_*` überschreiben API-Runtime-Einstellungen;
- `LogStormCore` übergibt einen konsistenten Runtime-Kontext an API und CLI.

Beispiel:

```python
from core import LogStormCore, build_settings

settings = build_settings()
core = LogStormCore(settings)
db_path = core.settings.api.collector_db_path
default_schedule = core.default_schedule_payload()
```

## Datenformate

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

LogStorm kann die Anwesenheitsanalyse über HTTP bereitstellen:

```bash
LOGSTORM_COLLECTOR_DB_PATH=/path/to/events.db \
LOGSTORM_API_TOKEN=change-me \
uvicorn api.app:app --host 0.0.0.0 --port 8000
```

`api.app` liest diese Werte über `LogStormCore`.

Endpoints:

- `GET /health`
- `POST /attendance/analyze`

`POST /attendance/analyze` akzeptiert optional `aliases: string[]`. Ereignisse, deren `employeeNoString` mit einem dieser Aliases übereinstimmt, werden für die aktuelle Analyseantwort in die kanonische `employee_id` zusammengeführt.

`LOGSTORM_API_TOKEN` ist für lokale Entwicklung optional. Wenn es gesetzt ist, müssen Clients `Authorization: Bearer <token>` senden.

Wenn EUSRR keinen `schedule` sendet, verwendet LogStorm den Standardzeitplan aus `core/settings.py`. Der Fallback wird gesteuert über:

- `LOGSTORM_ALLOW_DEFAULT_SCHEDULE=false` - Anfragen ohne `schedule` ablehnen;
- `LOGSTORM_DEFAULT_START_TIME=08:00`;
- `LOGSTORM_DEFAULT_END_TIME=17:00`;
- `LOGSTORM_DEFAULT_EXPECTED_HOURS=9`;
- `LOGSTORM_DEFAULT_WORKDAYS=Monday,Tuesday,Wednesday,Thursday,Friday`.

`file_type="auto"` erkennt auch `.db`, `.sqlite` und `.sqlite3`.

Unterstützte Zutrittskontrollereignisse:

- `minor=75` - erfolgreicher Eingang;
- `minor=104` - erfolgreicher Ausgang;
- `minor=21/22` - Tür geöffnet/geschlossen;
- `minor=76` - unbekanntes Gesicht.

## Mitarbeitermapping

Das Sample Mapping `data/person.sample.json` verwendet dieses Format:

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

`PersonMapper` kann:

- Anzeigenamen ändern;
- individuelle Zeitpläne anwenden;
- mehrere IDs desselben Mitarbeiters über `aliases` zusammenführen;
- als Profilquelle für `AttendanceService` arbeiten.

## Collector

Der Collector sammelt Zutrittskontrollereignisse und schreibt sie nach NDJSON und SQLite:

```bash
python main.py collector --once
python main.py collector --config collector/collector.local.py --once  # legacy override
```

Für Tests ist kein Netzwerkzugriff erforderlich: Collector-Verhalten wird über Konfiguration, State Tracking, Deduplizierung und lokale Speicherung geprüft.

Standardmäßig liest der Collector die Konfiguration aus `.env` / `core.settings`. `collector.local.py` bleibt nur als optionaler Legacy-Override mit einem Top-Level-`CONFIG`-Dictionary. JSON-Konfigurationen werden nur zur Rückwärtskompatibilität gelesen.

## Struktur

Detaillierte Architekturgrenzen: `docs/ARCHITECTURE.md`.

```text
LogStorm/
├── analyzer/           # Anwesenheitsanalyse, Loader, Validatoren, Berichte
├── api/                # FastAPI-Schicht
├── collector/          # Ereignis-Collector und Storage
├── core/               # Einstellungen, gemeinsame Modelle, Repositories
├── data/               # lokale Test-/Demo-Daten
├── tests/              # pytest-Suite
├── tools/export/       # Export von Geräteereignissen
└── utils/              # Datum, Excel-Helfer, Exceptions, Logging
```

## Nicht Im Aktiven Umfang

- GUI ist aus dem aktiven Umfang entfernt.
- AI-Integration ist aus aktuellem Code und Dokumentation entfernt.
- Alte Pfade wie `LogsCam/`, `path/person_prefs.json`, `run_gui.py`, `gui/`, `gui_app.py`, `gui_config.py`, `gui_app_fluent.py`, `config.json` und `config.py` gehören nicht zur aktuellen Struktur.
