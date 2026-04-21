from pathlib import Path

import pandas as pd

from config import LOGS_FILE, PERSON_MAPPING_FILE, OUTPUT_EXCEL_FILE
from reporters import ExcelReporter
from services import AttendanceService, DataLoader, PersonMapper
from validators.absence_validator import AbsenceValidator


def test_public_config_points_to_existing_sample_data():
    assert Path(LOGS_FILE).exists()
    assert PERSON_MAPPING_FILE == "" or Path(PERSON_MAPPING_FILE).exists()
    assert Path("person.json").exists()
    assert OUTPUT_EXCEL_FILE.startswith("reports/")


def test_core_csv_analysis_pipeline_with_sample_data():
    df = DataLoader.load_logs(LOGS_FILE, file_type="csv")
    prefs = {}
    df = DataLoader.filter_known_users(df, prefs)

    records = AttendanceService(df, prefs).analyze_all()

    assert len(records) > 0
    assert all(record.display_name for record in records)


def test_core_ndjson_analysis_pipeline_with_sample_data():
    mapper = PersonMapper("person.json")
    df = DataLoader.load_logs(
        ["data/vhod.ndjson", "data/vihod.ndjson"],
        file_type="ndjson",
        person_mapper=mapper,
    )

    assert not df.empty
    assert pd.api.types.is_datetime64_any_dtype(df["timestamp"])
    assert "19" in set(df["name"])
    assert "666" not in set(df["name"])


def test_real_events_db_is_supported_when_present():
    db_path = Path("events.db")
    if not db_path.exists():
        return

    mapper = PersonMapper("person.json")
    df = DataLoader.load_logs(str(db_path), file_type="sqlite", person_mapper=mapper)

    assert len(df) > 0
    assert {"timestamp", "date", "name", "display_name"}.issubset(df.columns)


def test_excel_reporter_writes_to_tmp_path(tmp_path):
    df = DataLoader.load_logs(LOGS_FILE, file_type="csv")
    prefs = {}
    df = DataLoader.filter_known_users(df, prefs)
    records = AttendanceService(df, prefs).analyze_all()[:10]

    output = tmp_path / "report.xlsx"
    ok = ExcelReporter(records).generate_report(str(output))

    assert ok is True
    assert output.exists()


def test_absence_validator_handles_empty_dataframe():
    empty = pd.DataFrame(columns=["date", "name"])
    validator = AbsenceValidator(empty, {})

    assert validator.detect_mass_absence_days() == set()
    assert validator.detect_critical_absence_days() == set()
