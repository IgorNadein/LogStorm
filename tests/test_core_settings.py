from core import LogStormCore, build_settings


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
