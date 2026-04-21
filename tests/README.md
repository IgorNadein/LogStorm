# Tests

Главная команда:

```bash
python -m pytest
```

Тестовые слои:

- config/unit: `test_config.py`, `test_utils.py`, `test_weekend_logic.py`;
- mapping/core: `test_mapping_optional.py`, `test_melanya_mapping.py`;
- public API/integration: `test_public_api.py`;
- collector: `test_collector_api.py`, `test_collector_storage.py`;
- SQLAlchemy collector DB loading: `test_collector_storage.py`, `test_public_api.py`;
- DI: `test_di_container.py`.

Фактические fixtures:

- `data/attendance.csv`;
- `data/vhod.ndjson`;
- `data/vihod.ndjson`;
- `person.json`.
