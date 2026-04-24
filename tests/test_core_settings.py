from sqlalchemy.pool import NullPool

from core import LogStormCore, build_settings
from core.db import create_collector_engine


def test_core_uses_config_defaults_as_sources_of_truth():
    core = LogStormCore.from_sources(env={})

    assert core.settings.cli.logs_file == "data/attendance.csv"
    assert core.settings.cli.person_mapping_file == ""
    assert core.settings.cli.output_excel_file.startswith("reports/")
    assert core.settings.api.collector_db_path == "events.db"
    assert core.settings.api.api_token == ""
    assert core.settings.api.allow_default_schedule is True
    assert core.default_schedule_payload() == {
        "start_time": "08:00",
        "end_time": "17:00",
        "expected_hours": 9.0,
        "workdays": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        "date_overrides": [],
    }


def test_core_reads_api_settings_from_env():
    settings = build_settings(env={
        "LOGSTORM_COLLECTOR_DB_PATH": "/tmp/events.db",
        "LOGSTORM_API_TOKEN": "secret",
        "LOGSTORM_ALLOW_DEFAULT_SCHEDULE": "false",
        "LOGSTORM_DEFAULT_START_TIME": "10:00",
        "LOGSTORM_DEFAULT_END_TIME": "19:00",
        "LOGSTORM_DEFAULT_EXPECTED_HOURS": "8",
        "LOGSTORM_DEFAULT_WORKDAYS": "Monday,Saturday",
    })

    assert settings.api.collector_db_path == "/tmp/events.db"
    assert settings.api.api_token == "secret"
    assert settings.api.allow_default_schedule is False
    assert settings.api.default_schedule["start_time"] == "10:00"
    assert settings.api.default_schedule["end_time"] == "19:00"
    assert settings.api.default_schedule["expected_hours"] == 8.0
    assert settings.api.default_schedule["workdays"] == ["Monday", "Saturday"]
    assert settings.collector.sqlite_path == "/tmp/events.db"


def test_core_prefers_collector_db_url_over_legacy_path():
    settings = build_settings(env={
        "LOGSTORM_COLLECTOR_DB_PATH": "/tmp/events.db",
        "LOGSTORM_COLLECTOR_DB_URL": "postgresql+psycopg://user:pass@localhost/logstorm",
    })

    assert (
        settings.api.collector_db_path
        == "postgresql+psycopg://user:pass@localhost/logstorm"
    )
    assert (
        settings.collector.sqlite_path
        == "postgresql+psycopg://user:pass@localhost/logstorm"
    )


def test_core_builds_collector_settings_from_env():
    settings = build_settings(env={
        "LOGSTORM_COLLECTOR_DB_PATH": "/tmp/events.db",
        "LOGSTORM_COLLECTOR_NDJSON_PATH": "/tmp/events.ndjson",
        "LOGSTORM_COLLECTOR_LOG_FILE": "/tmp/collector.log",
        "LOGSTORM_COLLECTOR_INTERVAL_MINUTES": "5",
        "LOGSTORM_COLLECTOR_MAX_PARALLEL": "2",
        "LOGSTORM_COLLECTOR_INITIAL_DAYS": "7",
        "LOGSTORM_COLLECTOR_IMAGES_UNC_PATH": "//server/share/images",
        "LOGSTORM_COLLECTOR_IMAGES_ENABLED": "true",
    })

    assert settings.collector.sqlite_path == "/tmp/events.db"
    assert settings.collector.ndjson_path == "/tmp/events.ndjson"
    assert settings.collector.log_file == "/tmp/collector.log"
    assert settings.collector.interval_minutes == 5
    assert settings.collector.max_parallel == 2
    assert settings.collector.initial_days == 7
    assert settings.collector.images["enabled"] is True
    assert settings.collector.images["unc_path"] == "//server/share/images"


def test_core_explicit_api_settings_override_env():
    settings = build_settings(
        env={
            "LOGSTORM_COLLECTOR_DB_PATH": "/env/events.db",
            "LOGSTORM_API_TOKEN": "env-token",
        },
        collector_db_path="/explicit/events.db",
        api_token="explicit-token",
    )

    assert settings.api.collector_db_path == "/explicit/events.db"
    assert settings.api.api_token == "explicit-token"


def test_core_builds_collector_devices_from_json_env():
    settings = build_settings(env={
        "LOGSTORM_COLLECTOR_DEVICES_JSON": """
[
  {
    "name": "Камера входа",
    "host": "192.168.1.101",
    "user": "admin",
    "password": "CHANGE_ME",
    "enabled": true,
    "save_images": true
  },
  {
    "name": "Камера выхода",
    "host": "192.168.1.104",
    "user": "admin",
    "password": "CHANGE_ME",
    "enabled": true,
    "save_images": true
  },
  {
    "name": "Камера 2",
    "host": "192.168.1.102",
    "user": "admin",
    "password": "CHANGE_ME",
    "enabled": true,
    "save_images": true
  },
  {
    "name": "Камера 3",
    "host": "192.168.1.103",
    "user": "admin",
    "password": "CHANGE_ME",
    "enabled": true,
    "save_images": true
  }
]
""".strip(),
    })

    assert len(settings.collector.devices) == 4
    assert settings.collector.devices[1]["host"] == "192.168.1.104"
    assert settings.collector.devices[3]["name"] == "Камера 3"
    assert settings.collector.devices[0]["save_images"] is True


def test_create_collector_engine_reuses_engine_for_same_url_and_role():
    url = "postgresql+psycopg://user:pass@localhost/logstorm"

    engine1 = create_collector_engine(url, role="api")
    engine2 = create_collector_engine(url, role="api")

    assert engine1 is engine2
    assert engine1.pool.size() == 2


def test_create_collector_engine_uses_distinct_roles_and_pool_settings():
    url = "postgresql+psycopg://user:pass@localhost/logstorm"

    api_engine = create_collector_engine(url, role="api")
    collector_engine = create_collector_engine(url, role="collector")
    migration_engine = create_collector_engine(url, role="migration")

    assert api_engine is not collector_engine
    assert api_engine.pool.size() == 2
    assert collector_engine.pool.size() == 1
    assert isinstance(migration_engine.pool, NullPool)


def test_core_reuses_repository_instances():
    core = LogStormCore.from_sources(env={"LOGSTORM_COLLECTOR_DB_PATH": "events.db"})

    assert core.collector_repository() is core.collector_repository()
    assert (
        core.attendance_override_repository()
        is core.attendance_override_repository()
    )
