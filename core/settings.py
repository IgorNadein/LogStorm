"""Runtime settings for LogStorm.

This module intentionally follows a Django-like style: defaults are plain
module constants, environment overrides are explicit, and entrypoints receive
one resolved settings object from ``build_settings``.
"""

from __future__ import annotations

import os
from types import SimpleNamespace
from typing import Mapping, Optional

from config.analysis import analysis_config
from config.paths import paths_config
from services.collector_event_repository import CollectorEventRepository


# Project defaults. Keep them boring and visible.
LOGS_FILE = paths_config.logs_file
PERSON_MAPPING_FILE = paths_config.person_mapping_file
OUTPUT_EXCEL_FILE = paths_config.output_excel_file

COLLECTOR_DB_PATH = os.getenv("LOGSTORM_COLLECTOR_DB_PATH", "events.db")
API_TOKEN = os.getenv("LOGSTORM_API_TOKEN", "")
ALLOW_DEFAULT_SCHEDULE = os.getenv(
    "LOGSTORM_ALLOW_DEFAULT_SCHEDULE",
    "true",
).lower() in {"1", "true", "yes", "on"}

DEFAULT_SCHEDULE = {
    "workdays": list(analysis_config.default_schedule.workdays),
    "start_time": analysis_config.default_schedule.start_time,
    "end_time": analysis_config.default_schedule.end_time,
    "expected_hours": float(analysis_config.default_schedule.work_hours),
}


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
            collector_db_path=(
                collector_db_path
                or resolved_env.get("LOGSTORM_COLLECTOR_DB_PATH")
                or "events.db"
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
