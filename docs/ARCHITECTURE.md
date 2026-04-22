# LogStorm Architecture

LogStorm is one application with several entrypoints, not a set of independent
microservices. The current active applications are:

- `core/` - settings, shared models, shared repositories;
- `collector/` - access-control event collection and NDJSON/SQLite writing;
- `analyzer/` - attendance analysis, loaders, validators, reporters, EUSRR contract;
- `api/` - FastAPI transport for analyzer/core.

## Canonical Imports

New code should use these packages:

```python
from core import LogStormCore, build_settings
from core.models import AttendanceRecord, WorkSchedule, CollectorEvent
from core.repositories import CollectorEventRepository

from analyzer import DataLoader, AttendanceService, PersonMapper
from analyzer.reporters import ExcelReporter, SummaryReporter
from analyzer.validators import AbsenceValidator, TimeValidator
```

The previous experimental DI layer was removed. Runtime composition now happens
explicitly through `core.settings`, `LogStormCore`, API app factories and direct
service construction in entrypoints.

## Settings

`core/settings.py` is the single Python settings module for active code:

- API token and collector DB path;
- collector storage, devices and polling defaults;
- analyzer default schedule;
- CLI paths and report output.

Local runtime values are set through `LOGSTORM_*` environment variables.
JSON configuration is not a source of truth for the active application.

## Data Flow

```text
collector -> NDJSON/SQLite events.db
api       -> core repository -> analyzer -> response DTO
CLI       -> analyzer loaders -> analyzer service -> reports
```

`core.models.CollectorEvent` describes the shared SQLite contract. The
collector can continue writing through `sqlite3`; analyzer/API read through
`core.repositories.CollectorEventRepository`.

## Removed Legacy Layers

The old top-level packages `services`, `analyzers`, `validators`, `reporters`,
and `models` were compatibility wrappers only and have been removed from the
active project structure. Use the canonical imports above.

The previous GUI layer (`gui/`, `run_gui.py`, and `tools/app.py`) was removed
from active scope. Runtime operations should go through `main.py`, API,
collector, or focused tools.
