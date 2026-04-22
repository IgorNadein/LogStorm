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
        "--verbose",
    ])

    assert forwarded["argv"] == [
        "--config",
        "collector/test.py",
        "--once",
        "--verbose",
    ]
