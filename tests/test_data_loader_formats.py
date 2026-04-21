import json

import pandas as pd
import pytest

from collector.storage import EventStorage
from analyzer import DataLoader


def _collector_event(employee_id="001", serial=1, timestamp="2026-04-20T09:00:00"):
    return {
        "_device": "door-1",
        "_collected": "2026-04-20T10:00:00",
        "major": 5,
        "minor": 75,
        "time": timestamp,
        "employeeNoString": employee_id,
        "serialNo": serial,
        "name": "Raw Name",
    }


def test_csv_loader_reads_required_columns(tmp_path):
    csv_path = tmp_path / "events.csv"
    pd.DataFrame([
        {"timestamp": "2026-04-20T09:00:00", "name": "100"},
    ]).to_csv(csv_path, index=False)

    df = DataLoader.load_logs(str(csv_path), file_type="csv")

    assert list(df["name"]) == ["100"]
    assert pd.api.types.is_datetime64_any_dtype(df["timestamp"])
    assert df.iloc[0]["date"].isoformat() == "2026-04-20"


@pytest.mark.parametrize("suffix", [".db", ".sqlite", ".sqlite3"])
def test_sqlite_extensions_are_auto_detected(tmp_path, suffix):
    sqlite_path = tmp_path / f"events{suffix}"
    storage = EventStorage(str(tmp_path / "events.ndjson"), str(sqlite_path))
    storage.write_events([_collector_event(employee_id="001")])

    df = DataLoader.load_logs(str(sqlite_path))

    assert len(df) == 1
    assert df.iloc[0]["name"] == "001"


def test_explicit_sqlite_file_type_is_supported(tmp_path):
    sqlite_path = tmp_path / "events.anything"
    storage = EventStorage(str(tmp_path / "events.ndjson"), str(sqlite_path))
    storage.write_events([_collector_event(employee_id="100")])

    df = DataLoader.load_logs(str(sqlite_path), file_type="sqlite")

    assert df.iloc[0]["name"] == "100"


def test_ndjson_loader_skips_malformed_lines(tmp_path):
    ndjson = tmp_path / "events.ndjson"
    ndjson.write_text(
        json.dumps(_collector_event(employee_id="100"), ensure_ascii=False)
        + "\n{broken json\n",
        encoding="utf-8",
    )

    df = DataLoader.load_logs(str(ndjson), file_type="ndjson")

    assert len(df) == 1
    assert df.iloc[0]["name"] == "100"


def test_empty_ndjson_returns_empty_dataframe(tmp_path):
    ndjson = tmp_path / "empty.ndjson"
    ndjson.write_text("", encoding="utf-8")

    df = DataLoader.load_logs(str(ndjson), file_type="ndjson")

    assert df.empty


def test_missing_file_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        DataLoader.load_logs(str(tmp_path / "missing.csv"))


def test_malformed_collector_event_without_time_is_rejected(tmp_path):
    ndjson = tmp_path / "events.ndjson"
    event = _collector_event()
    event.pop("time")
    ndjson.write_text(json.dumps(event, ensure_ascii=False) + "\n", encoding="utf-8")

    with pytest.raises(KeyError):
        DataLoader.load_logs(str(ndjson), file_type="ndjson")


def test_missing_employee_id_falls_back_to_name(tmp_path):
    ndjson = tmp_path / "events.ndjson"
    event = _collector_event(employee_id="")
    event["name"] = "Fallback Name"
    ndjson.write_text(json.dumps(event, ensure_ascii=False) + "\n", encoding="utf-8")

    df = DataLoader.load_logs(str(ndjson), file_type="ndjson")

    assert df.iloc[0]["name"] == "Fallback Name"
