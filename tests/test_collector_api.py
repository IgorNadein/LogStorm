import json
import logging
from datetime import datetime

from collector.collector import (
    DEFAULT_CONFIG,
    EventTracker,
    build_request_conditions,
    load_config,
    save_default_config,
)
from collector.storage import EventStorage


def test_load_config_returns_default_when_missing(tmp_path):
    config = load_config(str(tmp_path / "missing.json"))

    assert config["request"]["page_size"] == DEFAULT_CONFIG["request"]["page_size"]
    assert config["devices"][0]["host"] == "192.168.1.101"


def test_save_default_config_writes_json(tmp_path):
    config_path = tmp_path / "collector.json"

    save_default_config(str(config_path))

    saved = json.loads(config_path.read_text(encoding="utf-8"))
    assert saved["interval_minutes"] == DEFAULT_CONFIG["interval_minutes"]
    assert "devices" in saved


def test_build_request_conditions_extends_end_time_and_uses_request_config():
    config = {"request": {"page_size": 50, "major": 5, "minor": 75}}

    cond = build_request_conditions(
        start_time="2026-04-20T00:00:00",
        end_time="2026-04-21T00:00:00",
        next_serial=123,
        config=config,
        save_images=True,
    )

    assert cond["maxResults"] == 50
    assert cond["major"] == 5
    assert cond["minor"] == 75
    assert cond["beginSerialNo"] == 123
    assert cond["picEnable"] is True
    assert cond["endTime"] == "2026-04-22T00:00:00"


def test_event_tracker_uses_storage_state(tmp_path):
    storage = EventStorage(str(tmp_path / "events.ndjson"))
    tracker = EventTracker(storage, initial_days=10)

    storage.update_collector_state(
        "door-1",
        last_serial=55,
        last_collect="2026-04-21T12:00:00",
    )

    assert tracker.get_last_serial("door-1") == 55
    assert tracker.get_last_collect_time("door-1") == "2026-04-21T12:00:00"
    assert tracker.get_start_time("door-1") == "2026-04-21T11:00:00"


def test_event_tracker_duplicate_cache_is_per_device(tmp_path):
    storage = EventStorage(str(tmp_path / "events.ndjson"))
    tracker = EventTracker(storage)

    assert tracker.is_duplicate("door-1", 10) is False
    assert tracker.is_duplicate("door-1", 10) is True
    assert tracker.is_duplicate("door-2", 10) is False


def test_setup_logging_does_not_crash(tmp_path):
    from collector.collector import setup_logging

    logger = setup_logging(str(tmp_path / "collector.log"), verbose=True)

    assert isinstance(logger, logging.Logger)
    assert logger.level == logging.DEBUG
