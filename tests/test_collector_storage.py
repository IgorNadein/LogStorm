import json
import sqlite3

from sqlalchemy import select
from sqlalchemy.orm import Session

from collector.migrate import migrate_collector_storage
from collector.storage import EventStorage
from core.repositories import CollectorEventRepository
from core.db import create_collector_engine
from core.models import AttendanceManualOverride
from analyzer import DataLoader, PersonMapper


def _event(device="door-1", serial=1, name="Employee Sample"):
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


def test_storage_iter_events_without_images_and_update_event(tmp_path):
    ndjson = tmp_path / "events.ndjson"
    storage = EventStorage(str(ndjson))
    storage.write_events([
        _event(serial=1),
        {
            **_event(serial=2),
            "_imagePath": str(tmp_path / "images" / "2.jpg"),
        },
    ])

    missing = list(storage.iter_events_without_images())

    assert [event["serialNo"] for event in missing] == [1]

    updated = {
        **missing[0],
        "_imagePath": str(tmp_path / "images" / "1.jpg"),
    }
    storage.update_event(updated)

    missing_after_update = list(storage.iter_events_without_images())
    assert missing_after_update == []

    repo = CollectorEventRepository(str(storage.sqlite_path))
    saved = repo.get_event(device="door-1", serial_no=1).to_event_dict()
    assert saved["_imagePath"].endswith("1.jpg")


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


def test_sqlalchemy_repository_filters_by_employee_ids(tmp_path):
    sqlite_path = tmp_path / "events.db"
    storage = EventStorage(str(tmp_path / "events.ndjson"), str(sqlite_path))
    storage.write_events([
        {**_event(serial=1), "employeeNoString": "100"},
        {**_event(serial=2), "employeeNoString": "200"},
        {**_event(serial=3), "employeeNoString": "300"},
    ])

    repo = CollectorEventRepository(str(sqlite_path))
    events = repo.load_raw_events(employee_id="100", employee_ids=["200", "200"])

    assert [event["employeeNoString"] for event in events] == ["100", "200"]


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
            "name": "Employee Delta",
        }
    ])

    mapper = PersonMapper("data/person.sample.json")
    df = DataLoader.load_logs(str(sqlite_path), person_mapper=mapper)

    assert len(df) == 1
    assert df.iloc[0]["name"] == "55"
    assert df.iloc[0]["display_name"] == "Employee Delta"
    assert df.iloc[0]["event_type"] == "pass_in"


def test_migrate_collector_storage_copies_events_states_and_overrides(tmp_path):
    source_db = tmp_path / "source.db"
    target_db = tmp_path / "target.db"
    storage = EventStorage(str(tmp_path / "events.ndjson"), str(source_db))
    storage.write_events([_event(serial=10), _event(serial=11)])
    storage.update_collector_state(
        "door-1",
        last_serial=11,
        last_collect="2026-04-21T10:00:00",
    )

    engine = create_collector_engine(str(source_db))
    with Session(engine) as session:
        session.add(
            AttendanceManualOverride(
                employee_id="42",
                date="2026-04-21",
                patch_data=json.dumps({"status": "present"}),
                source="test",
                note="manual",
                updated_at="2026-04-21T12:00:00",
            )
        )
        session.commit()

    counts = migrate_collector_storage(str(source_db), str(target_db))

    assert counts == {"events": 2, "states": 1, "overrides": 1}

    target_storage = EventStorage(str(tmp_path / "target.ndjson"), str(target_db))
    assert target_storage.get_event_count() == 2
    assert target_storage.get_last_serial("door-1") == 11
    assert target_storage.get_collector_state("door-1")["last_serial"] == 11

    target_engine = create_collector_engine(str(target_db))
    with Session(target_engine) as session:
        overrides = list(session.scalars(select(AttendanceManualOverride)))
        assert len(overrides) == 1
        assert overrides[0].employee_id == "42"


def test_migrate_collector_storage_refuses_non_empty_target_without_overwrite(tmp_path):
    source_db = tmp_path / "source.db"
    target_db = tmp_path / "target.db"
    source_storage = EventStorage(str(tmp_path / "source.ndjson"), str(source_db))
    target_storage = EventStorage(str(tmp_path / "target.ndjson"), str(target_db))
    source_storage.write_events([_event(serial=1)])
    target_storage.write_events([_event(serial=999)])

    try:
        migrate_collector_storage(str(source_db), str(target_db))
    except ValueError as exc:
        assert "not empty" in str(exc)
    else:  # pragma: no cover - explicit failure path
        raise AssertionError("Expected target non-empty migration to fail")

    counts = migrate_collector_storage(
        str(source_db),
        str(target_db),
        overwrite=True,
    )

    assert counts["events"] == 1
    assert target_storage.get_last_serial("door-1") == 1
