import json
import sqlite3

from collector.storage import EventStorage
from core.repositories import CollectorEventRepository
from analyzer import DataLoader, PersonMapper


def _event(device="door-1", serial=1, name="Иван"):
    return {
        "_device": device,
        "_collected": "2026-04-21T10:00:00",
        "serialNo": serial,
        "time": "2026-04-21T09:00:00+03:00",
        "employeeNoString": str(serial),
        "name": name,
    }


def test_storage_writes_ndjson_and_sqlite(tmp_path):
    ndjson = tmp_path / "events.ndjson"
    storage = EventStorage(str(ndjson))

    storage.write_events([_event(serial=1), _event(serial=2)])

    lines = ndjson.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["serialNo"] == 1
    assert storage.get_event_count() == 2
    assert storage.get_event_count("door-1") == 2
    assert storage.get_last_serial("door-1") == 2


def test_storage_initializes_expected_sqlite_schema(tmp_path):
    sqlite_path = tmp_path / "events.db"
    EventStorage(str(tmp_path / "events.ndjson"), str(sqlite_path))

    conn = sqlite3.connect(sqlite_path)
    try:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        event_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(events)")
        }
    finally:
        conn.close()

    assert {"events", "collector_state"}.issubset(tables)
    assert {
        "device",
        "serialNo",
        "time",
        "employeeNoString",
        "name",
        "event_data",
        "collected_at",
    }.issubset(event_columns)


def test_storage_replaces_duplicate_in_sqlite_but_keeps_raw_ndjson(tmp_path):
    ndjson = tmp_path / "events.ndjson"
    storage = EventStorage(str(ndjson))

    storage.write_events([_event(serial=7, name="first")])
    storage.write_events([_event(serial=7, name="updated")])

    assert len(ndjson.read_text(encoding="utf-8").splitlines()) == 2
    assert storage.get_event_count() == 1
    assert storage.get_last_serial("door-1") == 7


def test_collector_state_roundtrip(tmp_path):
    storage = EventStorage(str(tmp_path / "events.ndjson"))

    storage.update_collector_state(
        "door-1",
        last_serial=42,
        last_collect="2026-04-21T09:00:00",
    )

    state = storage.get_collector_state("door-1")
    assert state["last_serial"] == 42
    assert state["last_collect"] == "2026-04-21T09:00:00"
    assert state["updated_at"]


def test_rebuild_sqlite_from_ndjson_does_not_append_to_ndjson(tmp_path):
    ndjson = tmp_path / "events.ndjson"
    sqlite_path = tmp_path / "events.db"
    events = [_event(serial=1), _event(serial=2)]
    ndjson.write_text(
        "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in events),
        encoding="utf-8",
    )

    storage = EventStorage(str(ndjson), str(sqlite_path))
    sqlite_path.unlink()

    imported = storage.rebuild_sqlite_from_ndjson()

    assert imported == 2
    assert storage.get_event_count() == 2
    assert len(ndjson.read_text(encoding="utf-8").splitlines()) == 2


def test_sqlalchemy_repository_reads_collector_events(tmp_path):
    ndjson = tmp_path / "events.ndjson"
    sqlite_path = tmp_path / "events.db"
    storage = EventStorage(str(ndjson), str(sqlite_path))
    storage.write_events([_event(serial=10), _event(serial=11)])

    repo = CollectorEventRepository(str(sqlite_path))
    events = repo.load_raw_events()

    assert repo.count_events() == 2
    assert [event["serialNo"] for event in events] == [10, 11]
    assert repo.get_states() == []


def test_sqlalchemy_repository_filters_by_employee_period_and_device(tmp_path):
    sqlite_path = tmp_path / "events.db"
    storage = EventStorage(str(tmp_path / "events.ndjson"), str(sqlite_path))
    storage.write_events([
        _event(device="door-1", serial=1),
        {
            **_event(device="door-1", serial=2),
            "employeeNoString": "42",
            "time": "2026-04-22T09:00:00+03:00",
        },
        {
            **_event(device="door-2", serial=3),
            "employeeNoString": "42",
            "time": "2026-04-23T09:00:00+03:00",
        },
    ])

    repo = CollectorEventRepository(str(sqlite_path))
    events = repo.load_raw_events(
        start="2026-04-22",
        end="2026-04-23",
        devices=["door-1"],
        employee_id="42",
    )

    assert len(events) == 1
    assert events[0]["serialNo"] == 2
    assert events[0]["employeeNoString"] == "42"


def test_sqlalchemy_repository_handles_empty_database(tmp_path):
    sqlite_path = tmp_path / "events.db"
    EventStorage(str(tmp_path / "events.ndjson"), str(sqlite_path))

    repo = CollectorEventRepository(str(sqlite_path))

    assert repo.count_events() == 0
    assert repo.load_raw_events() == []


def test_data_loader_reads_sqlite_collector_database(tmp_path):
    ndjson = tmp_path / "events.ndjson"
    sqlite_path = tmp_path / "events.db"
    storage = EventStorage(str(ndjson), str(sqlite_path))
    storage.write_events([
        {
            "_device": "door-1",
            "_collected": "2026-04-21T10:00:00",
            "major": 5,
            "minor": 75,
            "time": "2026-04-21T09:00:00+03:00",
            "employeeNoString": "55",
            "serialNo": 55,
            "name": "Настя Самарина",
        }
    ])

    mapper = PersonMapper("data/person.sample.json")
    df = DataLoader.load_logs(str(sqlite_path), person_mapper=mapper)

    assert len(df) == 1
    assert df.iloc[0]["name"] == "55"
    assert df.iloc[0]["display_name"] == "Настя (Надежда) Самарина"
    assert df.iloc[0]["event_type"] == "pass_in"
