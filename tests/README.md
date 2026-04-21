# Tests

Главная команда:

```bash
python -m pytest -q
python -m compileall -q .
```

CI-контур без локальной рабочей БД:

```bash
python -m pytest -q -m "not realdb"
```

Опциональная проверка на рабочей collector DB:

```bash
python -m pytest -q -m realdb --real-db /home/lizerk/Dev/LogStorm/events.db
```

Тестовые слои:

- config/unit: `test_config.py`, `test_utils.py`;
- schedule/calendar: `test_schedule_calendar.py`, `test_weekend_logic.py`;
- attendance statuses: `test_attendance_status.py`;
- mapping/core: `test_mapping_optional.py`, `test_melanya_mapping.py`;
- data loaders: `test_data_loader_formats.py`;
- public API/integration: `test_public_api.py`, `test_attendance_integration.py`;
- EUSRR contract: `test_eusrr_contract.py`;
- collector: `test_collector_api.py`, `test_collector_storage.py`;
- SQLAlchemy collector DB loading: `test_collector_storage.py`, `test_real_events_db.py`;
- DI: `test_di_container.py`.

Фактические fixtures:

- `data/attendance.csv`;
- `data/vhod.ndjson`;
- `data/vihod.ndjson`;
- `person.json`.
