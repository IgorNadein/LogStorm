import logging
from datetime import datetime

import pytest
import requests
import collector.collector as collector_facade

from collector.collector import (
    Collector,
    DEFAULT_CONFIG,
    EventTracker,
    backfill_event_image,
    build_backfill_request_conditions,
    fetch_events_from_device,
    build_request_conditions,
    is_db_url,
    load_config,
    save_default_config,
)
from collector.storage import EventStorage


def test_load_config_returns_default_when_missing(tmp_path):
    config = load_config(str(tmp_path / "missing.py"))

    assert config["request"]["page_size"] == DEFAULT_CONFIG["request"]["page_size"]
    assert config["devices"][0]["host"] == "192.168.1.101"


def test_save_default_config_writes_python_config(tmp_path):
    config_path = tmp_path / "collector.local.py"

    save_default_config(str(config_path))

    saved = load_config(str(config_path))
    assert saved["interval_minutes"] == DEFAULT_CONFIG["interval_minutes"]
    assert "devices" in saved


def test_load_config_keeps_json_compatibility(tmp_path):
    config_path = tmp_path / "collector.json"
    config_path.write_text(
        '{"request": {"page_size": 77}, "devices": []}',
        encoding="utf-8",
    )

    config = load_config(str(config_path))

    assert config["request"]["page_size"] == 77


def test_load_config_merges_partial_json_with_defaults(tmp_path):
    config_path = tmp_path / "collector.json"
    config_path.write_text(
        '{"request": {"page_size": 77}, "images": {"enabled": true}}',
        encoding="utf-8",
    )

    config = load_config(str(config_path))

    assert config["request"]["page_size"] == 77
    assert config["request"]["timeout"] == DEFAULT_CONFIG["request"]["timeout"]
    assert config["images"]["enabled"] is True
    assert config["images"]["folder"] == DEFAULT_CONFIG["images"]["folder"]
    assert config["devices"] == DEFAULT_CONFIG["devices"]


def test_load_config_devices_override_replace_base_list(tmp_path):
    config_path = tmp_path / "collector.local.py"
    config_path.write_text(
        'CONFIG = {"devices": [{"name": "Only one", "host": "10.0.0.1"}]}',
        encoding="utf-8",
    )

    config = load_config(str(config_path))

    assert config["devices"] == [{"name": "Only one", "host": "10.0.0.1"}]


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


def test_build_backfill_request_conditions_uses_exact_serial_and_time_window():
    cond = build_backfill_request_conditions(
        {
            "serialNo": 123,
            "time": "2026-04-21T12:30:00+03:00",
        },
        _config(),
        window_minutes=3,
    )

    assert cond["beginSerialNo"] == 123
    assert cond["endSerialNo"] == 123
    assert cond["picEnable"] is True
    assert cond["startTime"] == "2026-04-21T12:27:00"
    assert cond["endTime"] == "2026-04-21T12:33:00"


def test_is_db_url_detects_sqlalchemy_urls():
    assert is_db_url("postgresql+psycopg://user:pass@db/logstorm") is True
    assert is_db_url("sqlite:///tmp/events.db") is True
    assert is_db_url("/tmp/events.db") is False


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


def test_collector_facade_exports_key_symbols():
    assert collector_facade.Collector is Collector
    assert callable(collector_facade.main)
    assert callable(collector_facade.fetch_events_from_device)
    assert callable(collector_facade.backfill_device_images)


class _FakeResponse:
    def __init__(self, status_code=200, payload=None, content_type="application/json"):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.headers = {"Content-Type": content_type}

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class _FakeSession:
    def __init__(self, responses=None, exception=None):
        self.responses = list(responses or [])
        self.exception = exception
        self.headers = {}
        self.posts = []
        self.closed = False

    def post(self, url, **kwargs):
        self.posts.append((url, kwargs))
        if self.exception:
            raise self.exception
        return self.responses.pop(0)

    def close(self):
        self.closed = True


def _logger():
    logger = logging.getLogger("test_collector_api")
    logger.handlers = []
    logger.addHandler(logging.NullHandler())
    return logger


def _device():
    return {
        "host": "camera.local",
        "name": "Entrance",
        "user": "admin",
        "password": "CHANGE_ME",
        "save_images": False,
    }


def _config():
    return {
        "request": {"page_size": 30, "major": 5, "minor": 75, "timeout": 1},
        "images": {"enabled": False},
    }


def _payload(events):
    return {"AcsEvent": {"InfoList": events}}


def test_fetch_events_success_and_empty_page(monkeypatch):
    session = _FakeSession([
        _FakeResponse(payload=_payload([
            {
                "serialNo": 10,
                "time": "2026-04-20T09:00:00",
                "employeeNoString": "100",
            }
        ])),
        _FakeResponse(payload=_payload([])),
    ])
    monkeypatch.setattr("collector.collector.requests.Session", lambda: session)

    result = fetch_events_from_device(
        _device(),
        "2026-04-20T00:00:00",
        "2026-04-20T23:59:59",
        _config(),
        _logger(),
        start_serial=1,
    )

    assert result.completed is True
    assert result.last_serial == 10
    assert result.last_event_time == "2026-04-20T09:00:00"
    assert len(result.events) == 1
    assert session.posts[0][1]["json"]["AcsEventCond"]["beginSerialNo"] == 1
    assert session.posts[1][1]["json"]["AcsEventCond"]["beginSerialNo"] == 11
    assert session.closed is True


def test_fetch_events_empty_first_page(monkeypatch):
    session = _FakeSession([_FakeResponse(payload=_payload([]))])
    monkeypatch.setattr("collector.collector.requests.Session", lambda: session)

    result = fetch_events_from_device(
        _device(),
        "2026-04-20T00:00:00",
        "2026-04-20T23:59:59",
        _config(),
        _logger(),
        start_serial=7,
    )

    assert result.events == []
    assert result.last_serial == 7
    assert result.completed is True


@pytest.mark.parametrize(
    "exception",
    [
        requests.exceptions.ReadTimeout("timeout"),
        requests.exceptions.ConnectionError("network"),
    ],
)
def test_fetch_events_network_errors_stop_collection(monkeypatch, exception):
    session = _FakeSession(exception=exception)
    monkeypatch.setattr("collector.collector.requests.Session", lambda: session)

    result = fetch_events_from_device(
        _device(),
        "2026-04-20T00:00:00",
        "2026-04-20T23:59:59",
        _config(),
        _logger(),
    )

    assert result.completed is False
    assert result.events == []


@pytest.mark.parametrize("status_code", [401, 500])
def test_fetch_events_http_errors_stop_collection(monkeypatch, status_code):
    session = _FakeSession([_FakeResponse(status_code=status_code)])
    monkeypatch.setattr("collector.collector.requests.Session", lambda: session)

    result = fetch_events_from_device(
        _device(),
        "2026-04-20T00:00:00",
        "2026-04-20T23:59:59",
        _config(),
        _logger(),
    )

    assert result.completed is False
    assert result.events == []


def test_fetch_events_device_error_status_stops_collection(monkeypatch):
    session = _FakeSession([
        _FakeResponse(payload={"statusCode": 4, "statusString": "bad request"})
    ])
    monkeypatch.setattr("collector.collector.requests.Session", lambda: session)

    result = fetch_events_from_device(
        _device(),
        "2026-04-20T00:00:00",
        "2026-04-20T23:59:59",
        _config(),
        _logger(),
    )

    assert result.completed is False


def test_fetch_events_invalid_json_stops_collection(monkeypatch):
    session = _FakeSession([_FakeResponse(payload=ValueError("bad json"))])
    monkeypatch.setattr("collector.collector.requests.Session", lambda: session)

    result = fetch_events_from_device(
        _device(),
        "2026-04-20T00:00:00",
        "2026-04-20T23:59:59",
        _config(),
        _logger(),
    )

    assert result.completed is False


def test_fetch_events_without_employee_or_serial_is_preserved(monkeypatch):
    session = _FakeSession([
        _FakeResponse(payload=_payload([{"time": "2026-04-20T09:00:00"}])),
        _FakeResponse(payload=_payload([])),
    ])
    monkeypatch.setattr("collector.collector.requests.Session", lambda: session)

    result = fetch_events_from_device(
        _device(),
        "2026-04-20T00:00:00",
        "2026-04-20T23:59:59",
        _config(),
        _logger(),
        start_serial=5,
    )

    assert result.completed is True
    assert result.events == [{"time": "2026-04-20T09:00:00"}]
    assert result.last_serial == 5


def test_backfill_event_image_updates_event_when_camera_returns_photo(monkeypatch):
    session = _FakeSession([
        _FakeResponse(payload=_payload([
            {
                "serialNo": 10,
                "time": "2026-04-20T09:00:00",
                "employeeNoString": "100",
                "pictureURL": "cid:photo-1",
            }
        ]), content_type="multipart/mixed"),
    ])
    monkeypatch.setattr("collector.collector.requests.Session", lambda: session)
    monkeypatch.setattr(
        "collector.collector.parse_multipart_response",
        lambda *args, **kwargs: (
            _payload([
                {
                    "serialNo": 10,
                    "time": "2026-04-20T09:00:00",
                    "employeeNoString": "100",
                    "pictureURL": "cid:photo-1",
                }
            ]),
            {"cid:photo-1": b"image"},
        ),
    )

    def _fake_process_event_images(events, *args, **kwargs):
        events[0]["_imagePath"] = "images/100_10.jpg"
        return 1

    monkeypatch.setattr(
        "collector.collector.process_event_images",
        _fake_process_event_images,
    )

    updated = backfill_event_image(
        _device(),
        {
            "_device": "camera.local",
            "_device_name": "Entrance",
            "_collected": "2026-04-20T10:00:00",
            "serialNo": 10,
            "time": "2026-04-20T09:00:00",
            "employeeNoString": "100",
        },
        _config(),
        _logger(),
    )

    assert updated["_imagePath"] == "images/100_10.jpg"
    assert updated["_device"] == "camera.local"
    assert session.closed is True


def test_collector_backfills_missing_images_in_sqlite(tmp_path, monkeypatch):
    storage = EventStorage(str(tmp_path / "events.ndjson"), str(tmp_path / "events.db"))
    storage.write_events([
        {
            "_device": "camera.local",
            "_device_name": "Entrance",
            "_collected": "2026-04-20T10:00:00",
            "serialNo": 10,
            "time": "2026-04-20T09:00:00",
            "employeeNoString": "100",
        }
    ])
    config = {
        **_config(),
        "storage": {
            "ndjson": str(tmp_path / "events.ndjson"),
            "sqlite": str(tmp_path / "events.db"),
        },
        "devices": [_device()],
    }

    def _fake_backfill_device_images(
        device,
        device_events,
        storage,
        config,
        logger,
    ):
        event = device_events[0]
        storage.update_event_image(
            event["_device"],
            int(event["serialNo"]),
            str(tmp_path / "images" / "100_10.jpg"),
        )
        return 1, 0

    monkeypatch.setattr(
        "collector.collector.backfill_device_images",
        _fake_backfill_device_images,
    )

    collector = Collector(config, _logger())

    updated = collector.backfill_missing_images()

    assert updated == 1
    events_without_images = list(collector.storage.iter_events_without_images())
    assert events_without_images == []


def test_collector_collect_once_uses_facade_fetch_wrapper(tmp_path, monkeypatch):
    config = {
        **_config(),
        "storage": {
            "ndjson": str(tmp_path / "events.ndjson"),
            "sqlite": str(tmp_path / "events.db"),
        },
        "devices": [{**_device(), "save_images": False}],
    }

    def _fake_fetch_events(*args, **kwargs):
        return collector_facade.FetchResult(
            events=[
                {
                    "serialNo": 10,
                    "time": "2026-04-20T09:00:00",
                    "employeeNoString": "100",
                }
            ],
            last_serial=10,
            completed=True,
            last_event_time="2026-04-20T09:00:00",
        )

    monkeypatch.setattr(collector_facade, "fetch_events_from_device", _fake_fetch_events)

    collector = Collector(config, _logger())
    new_count = collector.collect_once()

    assert new_count == 1
    assert collector.storage.get_event_count() == 1


def test_collector_accepts_sqlalchemy_db_url(tmp_path):
    config = {
        **_config(),
        "storage": {
            "ndjson": str(tmp_path / "events.ndjson"),
            "sqlite": "sqlite:///" + str(tmp_path / "events.db"),
        },
        "devices": [],
    }

    collector = Collector(config, _logger())

    assert collector.sqlite_file == config["storage"]["sqlite"]


def test_collector_main_uses_defaults_when_config_file_is_missing(tmp_path, monkeypatch):
    captured = {}

    class _FakeCollector:
        def __init__(self, config, logger):
            captured["config"] = config

        def collect_once(self):
            captured["collect_once"] = True

        def stop(self):
            return None

    monkeypatch.setattr(collector_facade, "Collector", _FakeCollector)
    monkeypatch.setattr(collector_facade, "get_app_dir", lambda: str(tmp_path))
    monkeypatch.setattr(
        collector_facade,
        "setup_logging",
        lambda *args, **kwargs: _logger(),
    )

    collector_facade.main(["--once"])

    assert captured["collect_once"] is True
    assert captured["config"]["storage"]["sqlite"] == DEFAULT_CONFIG["storage"]["sqlite"]
    assert captured["config"]["devices"] == DEFAULT_CONFIG["devices"]
