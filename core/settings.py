"""Runtime settings for LogStorm.

This module intentionally follows a Django-like style: defaults are plain
module constants, environment overrides are explicit, and entrypoints receive
one resolved settings object from ``build_settings``.
"""

from __future__ import annotations

import json
import os
from types import SimpleNamespace
from typing import Mapping, Optional

from core.repositories import (
    AttendanceManualOverrideRepository,
    CollectorEventRepository,
)


# Project defaults. Keep them boring and visible.
LOGS_FILE = os.getenv("LOGSTORM_LOGS_FILE", "data/attendance.csv")
PERSON_MAPPING_FILE = os.getenv("LOGSTORM_PERSON_MAPPING_FILE", "")
SAMPLE_PERSON_MAPPING_FILE = "data/person.sample.json"
OUTPUT_EXCEL_FILE = os.getenv(
    "LOGSTORM_OUTPUT_EXCEL_FILE",
    "reports/attendance_report.xlsx",
)

# Analyzer defaults.
DEFAULT_START_TIME = os.getenv("LOGSTORM_DEFAULT_START_TIME", "08:00")
DEFAULT_END_TIME = os.getenv("LOGSTORM_DEFAULT_END_TIME", "17:00")
DEFAULT_WORK_HOURS = float(os.getenv("LOGSTORM_DEFAULT_EXPECTED_HOURS", "9"))
DEFAULT_SCHEDULE = {
    "workdays": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
    "start_time": DEFAULT_START_TIME,
    "end_time": DEFAULT_END_TIME,
    "expected_hours": DEFAULT_WORK_HOURS,
    "work_hours": DEFAULT_WORK_HOURS,
}

OVERTIME_THRESHOLD = int(os.getenv("LOGSTORM_OVERTIME_THRESHOLD", "10"))
LATE_THRESHOLD_MINUTES = int(os.getenv("LOGSTORM_LATE_THRESHOLD_MINUTES", "5"))
CRITICAL_LATE_MINUTES = int(os.getenv("LOGSTORM_CRITICAL_LATE_MINUTES", "180"))
CRITICAL_UNDERWORK_HOURS = int(
    os.getenv("LOGSTORM_CRITICAL_UNDERWORK_HOURS", "3")
)
MASS_ABSENCE_THRESHOLD = float(os.getenv("LOGSTORM_MASS_ABSENCE_THRESHOLD", "0.8"))
CRITICAL_ABSENCE_THRESHOLD = float(
    os.getenv("LOGSTORM_CRITICAL_ABSENCE_THRESHOLD", "1.0")
)
NIGHT_HOUR_START = int(os.getenv("LOGSTORM_NIGHT_HOUR_START", "23"))
NIGHT_HOUR_END = int(os.getenv("LOGSTORM_NIGHT_HOUR_END", "3"))
TOP_N_USERS = int(os.getenv("LOGSTORM_TOP_N_USERS", "5"))
MAX_SUSPICIOUS_DETAILS = int(os.getenv("LOGSTORM_MAX_SUSPICIOUS_DETAILS", "10"))

# Localization.
DAYS_RU = {
    "Monday": "Понедельник",
    "Tuesday": "Вторник",
    "Wednesday": "Среда",
    "Thursday": "Четверг",
    "Friday": "Пятница",
    "Saturday": "Суббота",
    "Sunday": "Воскресенье",
}
DAYS_ORDER = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]
MONTHS_RU = {
    1: "Январь",
    2: "Февраль",
    3: "Март",
    4: "Апрель",
    5: "Май",
    6: "Июнь",
    7: "Июль",
    8: "Август",
    9: "Сентябрь",
    10: "Октябрь",
    11: "Ноябрь",
    12: "Декабрь",
}

# Excel formatting.
HEADER_COLOR = "4472C4"
SUMMARY_HEADER_COLOR = "9966CC"
LATE_BG_COLOR = "FFE699"
OVERTIME_BG_COLOR = "C6EFCE"
SUSPICIOUS_BG_COLOR = "FFB3B3"
LATE_CELL_COLOR = "FFA500"
UNDERWORK_CELL_COLOR = "FFFF00"
OVERTIME_CELL_COLOR = "00B050"
SUSPICIOUS_CELL_COLOR = "8B0000"
TECHNICAL_FILL_COLOR = "FF0000"
SHEET_MAIN_REPORT = "Отчет по дням"
SHEET_SUSPICIOUS = "Подозрительные случаи"
SHEET_MONTH_PREFIX = "Месяц "


def _env_bool(env: Mapping[str, str], name: str, default: bool) -> bool:
    raw = env.get(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


def _env_float(env: Mapping[str, str], name: str, default: float) -> float:
    raw = env.get(name)
    if raw is None:
        return default
    return float(raw)


def _env_csv(env: Mapping[str, str], name: str, default: list[str]) -> list[str]:
    raw = env.get(name)
    if raw is None:
        return list(default)
    return [item.strip() for item in raw.split(",") if item.strip()]


# Collector defaults.
def _collector_db_setting(
    env: Mapping[str, str] | None = None,
    *,
    override: str | None = None,
) -> str:
    resolved_env = os.environ if env is None else env
    return (
        override
        or resolved_env.get("LOGSTORM_COLLECTOR_DB_URL")
        or resolved_env.get("LOGSTORM_COLLECTOR_DB_PATH")
        or "events.db"
    )


DEFAULT_COLLECTOR_DEVICES = [
    {
        "name": "Камера входа",
        "host": "192.168.1.101",
        "user": "admin",
        "password": "CHANGE_ME",
        "enabled": True,
    },
    {
        "name": "Камера выхода",
        "host": "192.168.1.102",
        "user": "admin",
        "password": "CHANGE_ME",
        "enabled": True,
    },
]


def _build_collector_request(env: Mapping[str, str]) -> dict[str, int]:
    return {
        "page_size": int(env.get("LOGSTORM_COLLECTOR_PAGE_SIZE", "30")),
        "timeout": int(env.get("LOGSTORM_COLLECTOR_TIMEOUT_SECONDS", "180")),
        "retries": int(env.get("LOGSTORM_COLLECTOR_RETRIES", "3")),
        "major": int(env.get("LOGSTORM_COLLECTOR_EVENT_MAJOR", "5")),
        "minor": int(env.get("LOGSTORM_COLLECTOR_EVENT_MINOR", "0")),
    }


def _build_collector_images(env: Mapping[str, str]) -> dict[str, object]:
    images = {
        "enabled": _env_bool(env, "LOGSTORM_COLLECTOR_IMAGES_ENABLED", False),
        "folder": env.get("LOGSTORM_COLLECTOR_IMAGES_FOLDER", "images"),
        "format": env.get(
            "LOGSTORM_COLLECTOR_IMAGES_FORMAT",
            "{date}/{employeeNoString}_{serialNo}.jpg",
        ),
    }
    unc_path = env.get("LOGSTORM_COLLECTOR_IMAGES_UNC_PATH")
    if unc_path:
        images["unc_path"] = unc_path
    return images


def _device_prefix_present(env: Mapping[str, str], index: int) -> bool:
    prefix = f"LOGSTORM_DEVICE_{index}_"
    return any(key.startswith(prefix) for key in env)


def _build_indexed_device(
    env: Mapping[str, str],
    index: int,
    default: Mapping[str, object] | None = None,
) -> dict[str, object]:
    fallback = dict(default or {})
    default_save_images = bool(
        fallback.get(
            "save_images",
            _env_bool(env, "LOGSTORM_COLLECTOR_IMAGES_ENABLED", False),
        )
    )
    return {
        "name": env.get(
            f"LOGSTORM_DEVICE_{index}_NAME",
            str(fallback.get("name", f"Камера {index}")),
        ),
        "host": env.get(
            f"LOGSTORM_DEVICE_{index}_HOST",
            str(fallback.get("host", "")),
        ),
        "user": env.get(
            f"LOGSTORM_DEVICE_{index}_USER",
            str(fallback.get("user", "admin")),
        ),
        "password": env.get(
            f"LOGSTORM_DEVICE_{index}_PASSWORD",
            str(fallback.get("password", "password")),
        ),
        "enabled": _env_bool(
            env,
            f"LOGSTORM_DEVICE_{index}_ENABLED",
            bool(fallback.get("enabled", True)),
        ),
        "save_images": _env_bool(
            env,
            f"LOGSTORM_DEVICE_{index}_SAVE_IMAGES",
            default_save_images,
        ),
    }


def _build_collector_devices(env: Mapping[str, str]) -> list[dict[str, object]]:
    raw = env.get("LOGSTORM_COLLECTOR_DEVICES_JSON")
    if raw:
        parsed = json.loads(raw)
        if not isinstance(parsed, list) or not all(
            isinstance(item, dict) for item in parsed
        ):
            raise ValueError(
                "LOGSTORM_COLLECTOR_DEVICES_JSON must be a JSON array of objects"
            )
        return [dict(item) for item in parsed]

    devices = [
        _build_indexed_device(env, index, default)
        for index, default in enumerate(DEFAULT_COLLECTOR_DEVICES, start=1)
    ]

    for index in range(len(DEFAULT_COLLECTOR_DEVICES) + 1, 17):
        if _device_prefix_present(env, index):
            devices.append(_build_indexed_device(env, index))

    return devices


COLLECTOR_NDJSON_PATH = os.getenv(
    "LOGSTORM_COLLECTOR_NDJSON_PATH",
    "events.ndjson",
)
COLLECTOR_DB_PATH = _collector_db_setting()
COLLECTOR_LOG_FILE = os.getenv("LOGSTORM_COLLECTOR_LOG_FILE", "collector.log")
COLLECTOR_INTERVAL_MINUTES = int(
    os.getenv("LOGSTORM_COLLECTOR_INTERVAL_MINUTES", "15")
)
COLLECTOR_MAX_PARALLEL = int(os.getenv("LOGSTORM_COLLECTOR_MAX_PARALLEL", "4"))
COLLECTOR_INITIAL_DAYS = int(os.getenv("LOGSTORM_COLLECTOR_INITIAL_DAYS", "30"))
COLLECTOR_REQUEST = _build_collector_request(os.environ)
COLLECTOR_IMAGES = _build_collector_images(os.environ)
COLLECTOR_DEVICES = _build_collector_devices(os.environ)
API_TOKEN = os.getenv("LOGSTORM_API_TOKEN", "")
ALLOW_DEFAULT_SCHEDULE = os.getenv(
    "LOGSTORM_ALLOW_DEFAULT_SCHEDULE",
    "true",
).lower() in {"1", "true", "yes", "on"}
PHOTO_PATH_REWRITES = os.getenv("LOGSTORM_PHOTO_PATH_REWRITES", "")


def _env_path_rewrites(env: Mapping[str, str]) -> list[tuple[str, str]]:
    raw = env.get("LOGSTORM_PHOTO_PATH_REWRITES", PHOTO_PATH_REWRITES)
    rewrites = []
    for item in raw.split(";"):
        if not item.strip() or "=" not in item:
            continue
        source, target = item.split("=", 1)
        source = source.strip()
        target = target.strip()
        if source and target:
            rewrites.append((source, target))
    return rewrites


def build_default_schedule(env: Optional[Mapping[str, str]] = None) -> dict:
    resolved_env = os.environ if env is None else env
    return {
        "workdays": _env_csv(
            resolved_env,
            "LOGSTORM_DEFAULT_WORKDAYS",
            DEFAULT_SCHEDULE["workdays"],
        ),
        "start_time": resolved_env.get(
            "LOGSTORM_DEFAULT_START_TIME",
            DEFAULT_SCHEDULE["start_time"],
        ),
        "end_time": resolved_env.get(
            "LOGSTORM_DEFAULT_END_TIME",
            DEFAULT_SCHEDULE["end_time"],
        ),
        "expected_hours": _env_float(
            resolved_env,
            "LOGSTORM_DEFAULT_EXPECTED_HOURS",
            DEFAULT_SCHEDULE["expected_hours"],
        ),
    }


def build_settings(
    *,
    env: Optional[Mapping[str, str]] = None,
    collector_db_path: Optional[str] = None,
    api_token: Optional[str] = None,
) -> SimpleNamespace:
    resolved_env = os.environ if env is None else env
    return SimpleNamespace(
        api=SimpleNamespace(
            collector_db_path=_collector_db_setting(
                resolved_env,
                override=collector_db_path,
            ),
            api_token=(
                api_token
                if api_token is not None
                else resolved_env.get("LOGSTORM_API_TOKEN", "")
            ),
            allow_default_schedule=_env_bool(
                resolved_env,
                "LOGSTORM_ALLOW_DEFAULT_SCHEDULE",
                True,
            ),
            default_schedule=build_default_schedule(resolved_env),
            photo_path_rewrites=_env_path_rewrites(resolved_env),
        ),
        collector=SimpleNamespace(
            ndjson_path=resolved_env.get(
                "LOGSTORM_COLLECTOR_NDJSON_PATH",
                COLLECTOR_NDJSON_PATH,
            ),
            sqlite_path=_collector_db_setting(
                resolved_env,
                override=collector_db_path,
            ),
            log_file=resolved_env.get(
                "LOGSTORM_COLLECTOR_LOG_FILE",
                COLLECTOR_LOG_FILE,
            ),
            interval_minutes=int(resolved_env.get(
                "LOGSTORM_COLLECTOR_INTERVAL_MINUTES",
                str(COLLECTOR_INTERVAL_MINUTES),
            )),
            max_parallel=int(resolved_env.get(
                "LOGSTORM_COLLECTOR_MAX_PARALLEL",
                str(COLLECTOR_MAX_PARALLEL),
            )),
            initial_days=int(resolved_env.get(
                "LOGSTORM_COLLECTOR_INITIAL_DAYS",
                str(COLLECTOR_INITIAL_DAYS),
            )),
            devices=_build_collector_devices(resolved_env),
            request=_build_collector_request(resolved_env),
            images=_build_collector_images(resolved_env),
        ),
        cli=SimpleNamespace(
            logs_file=LOGS_FILE,
            person_mapping_file=PERSON_MAPPING_FILE,
            output_excel_file=OUTPUT_EXCEL_FILE,
        ),
    )


class LogStormCore:
    """Runtime context shared by API, CLI and future entrypoints."""

    def __init__(self, settings: Optional[SimpleNamespace] = None):
        self.settings = settings or build_settings()

    @classmethod
    def from_sources(
        cls,
        *,
        env: Optional[Mapping[str, str]] = None,
        collector_db_path: Optional[str] = None,
        api_token: Optional[str] = None,
    ) -> "LogStormCore":
        return cls(
            build_settings(
                env=env,
                collector_db_path=collector_db_path,
                api_token=api_token,
            )
        )

    def default_schedule_payload(self) -> dict:
        schedule = self.settings.api.default_schedule
        return {
            "start_time": schedule["start_time"],
            "end_time": schedule["end_time"],
            "expected_hours": schedule["expected_hours"],
            "workdays": list(schedule["workdays"]),
            "date_overrides": [],
        }

    def collector_repository(self) -> CollectorEventRepository:
        return CollectorEventRepository(self.settings.api.collector_db_path)

    def attendance_override_repository(
        self,
    ) -> AttendanceManualOverrideRepository:
        return AttendanceManualOverrideRepository(
            self.settings.api.collector_db_path
        )


def build_collector_config(
    env: Optional[Mapping[str, str]] = None,
    *,
    collector_db_path: Optional[str] = None,
) -> dict:
    settings = build_settings(env=env, collector_db_path=collector_db_path)
    collector = settings.collector
    return {
        "storage": {
            "ndjson": collector.ndjson_path,
            "sqlite": collector.sqlite_path,
        },
        "log_file": collector.log_file,
        "interval_minutes": collector.interval_minutes,
        "max_parallel": collector.max_parallel,
        "initial_days": collector.initial_days,
        "images": dict(collector.images),
        "devices": [dict(device) for device in collector.devices],
        "request": dict(collector.request),
    }
