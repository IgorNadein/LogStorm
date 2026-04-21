"""LogStorm application core.

The core owns runtime settings and coordinates active entrypoints. Legacy
configuration modules still provide defaults, but API/CLI code should resolve
runtime values through this package.
"""

from .settings import (
    ALLOW_DEFAULT_SCHEDULE,
    API_TOKEN,
    COLLECTOR_DB_PATH,
    DEFAULT_SCHEDULE,
    LOGS_FILE,
    OUTPUT_EXCEL_FILE,
    PERSON_MAPPING_FILE,
    LogStormCore,
    build_default_schedule,
    build_settings,
)

__all__ = [
    "ALLOW_DEFAULT_SCHEDULE",
    "API_TOKEN",
    "COLLECTOR_DB_PATH",
    "DEFAULT_SCHEDULE",
    "LOGS_FILE",
    "LogStormCore",
    "OUTPUT_EXCEL_FILE",
    "PERSON_MAPPING_FILE",
    "build_default_schedule",
    "build_settings",
]
