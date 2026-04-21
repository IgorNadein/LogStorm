# LogStorm Architecture

LogStorm is one application with several entrypoints, not a set of independent
microservices. The current active applications are:

- `core/` - settings, shared models, shared repositories;
- `collector/` - access-control event collection and NDJSON/SQLite writing;
- `analyzer/` - attendance analysis, loaders, validators, reporters, EUSRR contract;
- `api/` - FastAPI transport for analyzer/core;
- `gui/` - paused legacy UI.

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

The old packages `services`, `analyzers`, `validators`, `reporters`, and
`models` are compatibility wrappers only.

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

## Compatibility Layer

Compatibility wrappers remain for older scripts and paused GUI code. They
should not be used by new code. Once external usage is verified, they can be
removed in a separate cleanup.
