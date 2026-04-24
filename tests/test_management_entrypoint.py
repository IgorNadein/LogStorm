import argparse

import main


def test_management_parser_exposes_expected_commands():
    parser = main.build_parser()

    command_action = next(
        action
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    )

    assert {
        "analyze",
        "api",
        "collector",
        "collector-migrate",
        "check",
        "mapping",
    }.issubset(command_action.choices)


def test_main_without_command_runs_analyze(monkeypatch):
    called = {}

    def fake_run_analyze(args):
        called["args"] = args

    monkeypatch.setattr(main, "run_analyze", fake_run_analyze)

    main.main([])

    assert called["args"].logs_file is None
    assert called["args"].mapping_file is None
    assert called["args"].output_file is None


def test_collector_command_forwards_arguments(monkeypatch):
    forwarded = {}

    def fake_collector_main(argv):
        forwarded["argv"] = argv

    import collector.collector

    monkeypatch.setattr(collector.collector, "main", fake_collector_main)

    main.main([
        "collector",
        "--config",
        "collector/test.py",
        "--once",
        "--backfill-images",
        "--backfill-limit",
        "500",
        "--verbose",
    ])

    assert forwarded["argv"] == [
        "--config",
        "collector/test.py",
        "--once",
        "--backfill-images",
        "--backfill-limit",
        "500",
        "--verbose",
    ]


def test_collector_command_omits_config_when_not_provided(monkeypatch):
    forwarded = {}

    def fake_collector_main(argv):
        forwarded["argv"] = argv

    import collector.collector

    monkeypatch.setattr(collector.collector, "main", fake_collector_main)

    main.main([
        "collector",
        "--once",
        "--verbose",
    ])

    assert forwarded["argv"] == [
        "--once",
        "--verbose",
    ]


def test_collector_migrate_command_forwards_arguments(monkeypatch):
    called = {}

    def fake_migrate(
        source_db,
        target_db,
        *,
        batch_size,
        overwrite,
        progress_callback,
    ):
        called["args"] = {
            "source_db": source_db,
            "target_db": target_db,
            "batch_size": batch_size,
            "overwrite": overwrite,
            "has_progress": progress_callback is not None,
        }
        return {"events": 1, "states": 2, "overrides": 3}

    import collector.migrate

    monkeypatch.setattr(collector.migrate, "migrate_collector_storage", fake_migrate)

    main.main([
        "collector-migrate",
        "--source-db",
        "events.db",
        "--batch-size",
        "250",
        "--overwrite",
        "--verbose",
    ])

    assert called["args"] == {
        "source_db": "events.db",
        "target_db": "events.db",
        "batch_size": 250,
        "overwrite": True,
        "has_progress": True,
    }


def test_collector_migrate_command_uses_target_override(monkeypatch):
    called = {}

    def fake_migrate(
        source_db,
        target_db,
        *,
        batch_size,
        overwrite,
        progress_callback,
    ):
        called["target_db"] = target_db
        return {"events": 0, "states": 0, "overrides": 0}

    import collector.migrate

    monkeypatch.setattr(collector.migrate, "migrate_collector_storage", fake_migrate)

    main.main([
        "collector-migrate",
        "--source-db",
        "old.db",
        "--target-db",
        "postgresql+psycopg://user:pass@localhost/logstorm",
    ])

    assert called["target_db"] == "postgresql+psycopg://user:pass@localhost/logstorm"
