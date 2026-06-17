**Idioma:** [English](README.md) | [Русский](README.ru.md) | [Deutsch](README.de.md) | [Español](README.es.md)

# LogStorm

LogStorm es un sistema backend y de procesamiento de datos para registros de eventos de control de acceso. Lee fuentes CSV, NDJSON y collector SQLite de sistemas estilo Hikvision/HiWatch, normaliza identificadores de empleados mediante reglas de mapeo, separa fallos técnicos de casos de asistencia relacionados con empleados y genera informes Excel.

El foco actual del proyecto es un core estable, collector, HTTP API y cobertura con pytest. La GUI fue retirada del alcance activo; el flujo principal pasa por `main.py`.

El repositorio público contiene solo datos demo sintéticos. Los registros reales de acceso, credenciales, informes generados y mappings privados deben permanecer fuera de Git.

## Estado Actual

- Core CLI: `main.py`
- Datos locales de smoke/integration: `data/attendance.csv`, `data/vhod.ndjson`, `data/vihod.ndjson`
- Ejemplo de mapeo de empleados para NDJSON: `data/person.sample.json`
- Runtime core: `core/settings.py` combina ajustes de API, CLI, collector y analyzer.
- Analyzer app: `analyzer/` contiene carga de datos, mapeo, análisis, validadores e informes.
- Collector: `collector/collector.py`, `collector/storage.py`
- Modelos/repositorios compartidos: `core/models/`, `core/repositories/`
- Exportación desde dispositivo: `tools/export/export_acs_events.py`

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Comprobar el entorno local:

```bash
python tools/check_environment.py
```

## Verificación

La fuente principal de verdad para el comportamiento actual es `pytest`.

```bash
python -m pytest
python -m pytest -q -m "not realdb"
python -m pytest -q -m realdb --real-db /home/lizerk/Dev/LogStorm/events.db
python -m compileall -q .
```

Capas cubiertas:

- unit: configuración, modelos, validadores, analizadores, utilidades;
- public API/core: `DataLoader`, `PersonMapper`, `AttendanceService`, `ExcelReporter`;
- contrato de servicio EUSRR: empleado, periodo, horario externo, excepciones de calendario;
- collector: configuración, cliente HTTP, state tracking, almacenamiento NDJSON y SQLite;
- SQLAlchemy: lectura de collector DB, filtros por empleado, periodo y dispositivo;
- integration: CSV/NDJSON/SQLite -> análisis -> salida DTO/Excel.

EUSRR se trata como la fuente de horarios, festivos, días laborales transferidos y días especiales. LogStorm aplica el calendario recibido a los eventos del collector. El `employee_id` de la solicitud debe coincidir con `employeeNoString` en los logs o estar conectado mediante `aliases` a nivel de solicitud.

## Management CLI

```bash
python main.py --help
python main.py analyze
python main.py api --db-path /home/lizerk/Dev/LogStorm/events.db
python main.py collector --once
python main.py check
```

`python main.py` sin subcomando conserva el comportamiento histórico e inicia `analyze`. Por defecto, el análisis lee:

- logs: `data/attendance.csv`;
- mapping: no definido, para que el sample CSV se analice sin filtrado;
- informe: `reports/attendance_report.xlsx`.

Estos valores se definen en `core/settings.py` y se leen mediante `LogStormCore`.

## Runtime Core

Los entrypoints activos deben recibir ajustes mediante `core.LogStormCore`. Este es el punto actual donde se combinan las fuentes de verdad de runtime:

- `core/settings.py` funciona como un módulo de settings estilo Django;
- los ajustes de análisis, rutas, formato y localización viven en un solo `core/settings.py`;
- las variables de entorno `LOGSTORM_*` sobrescriben los ajustes runtime de API;
- `LogStormCore` entrega un contexto runtime consistente a API y CLI.

Ejemplo:

```python
from core import LogStormCore, build_settings

settings = build_settings()
core = LogStormCore(settings)
db_path = core.settings.api.collector_db_path
default_schedule = core.default_schedule_payload()
```

## Formatos De Datos

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

LogStorm puede exponer el analizador de asistencia por HTTP:

```bash
LOGSTORM_COLLECTOR_DB_PATH=/path/to/events.db \
LOGSTORM_API_TOKEN=change-me \
uvicorn api.app:app --host 0.0.0.0 --port 8000
```

`api.app` lee estos valores mediante `LogStormCore`.

Endpoints:

- `GET /health`
- `POST /attendance/analyze`

`POST /attendance/analyze` acepta `aliases: string[]` opcional. Los eventos cuyo `employeeNoString` coincide con uno de estos aliases se fusionan en el `employee_id` canónico para la respuesta de análisis actual.

`LOGSTORM_API_TOKEN` es opcional para desarrollo local. Si está definido, los clientes deben enviar `Authorization: Bearer <token>`.

Si EUSRR no envía `schedule`, LogStorm usa el horario por defecto de `core/settings.py`. El fallback se controla con:

- `LOGSTORM_ALLOW_DEFAULT_SCHEDULE=false` - rechazar solicitudes sin `schedule`;
- `LOGSTORM_DEFAULT_START_TIME=08:00`;
- `LOGSTORM_DEFAULT_END_TIME=17:00`;
- `LOGSTORM_DEFAULT_EXPECTED_HOURS=9`;
- `LOGSTORM_DEFAULT_WORKDAYS=Monday,Tuesday,Wednesday,Thursday,Friday`.

`file_type="auto"` también reconoce `.db`, `.sqlite` y `.sqlite3`.

Eventos de control de acceso soportados:

- `minor=75` - entrada exitosa;
- `minor=104` - salida exitosa;
- `minor=21/22` - puerta abierta/cerrada;
- `minor=76` - rostro desconocido.

## Mapeo De Empleados

El sample mapping `data/person.sample.json` usa este formato:

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

`PersonMapper` puede:

- cambiar nombres visibles;
- aplicar horarios individuales;
- fusionar varios IDs del mismo empleado mediante `aliases`;
- funcionar como fuente de perfiles para `AttendanceService`.

## Collector

El collector recopila eventos de control de acceso y los escribe en NDJSON y SQLite:

```bash
python main.py collector --once
python main.py collector --config collector/collector.local.py --once  # legacy override
```

Los tests no requieren acceso a red: el collector se verifica mediante configuración, state tracking, deduplicación y almacenamiento local.

Por defecto, el collector lee configuración desde `.env` / `core.settings`. `collector.local.py` se mantiene solo como override legacy opcional con un diccionario `CONFIG` de nivel superior. Las configuraciones JSON se leen solo por compatibilidad hacia atrás.

## Estructura

Límites de arquitectura detallados: `docs/ARCHITECTURE.md`.

```text
LogStorm/
├── analyzer/           # análisis de asistencia, loaders, validadores, informes
├── api/                # capa FastAPI
├── collector/          # collector de eventos y storage
├── core/               # settings, modelos compartidos, repositories
├── data/               # datos locales de test/demo
├── tests/              # suite pytest
├── tools/export/       # exportación de eventos del dispositivo
└── utils/              # fechas, helpers Excel, excepciones, logging
```

## Fuera Del Alcance Activo

- La GUI fue retirada del alcance activo.
- La integración AI fue retirada del código y la documentación actuales.
- Rutas antiguas como `LogsCam/`, `path/person_prefs.json`, `run_gui.py`, `gui/`, `gui_app.py`, `gui_config.py`, `gui_app_fluent.py`, `config.json` y `config.py` no forman parte de la estructura actual.
