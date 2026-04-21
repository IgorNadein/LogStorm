# NDJSON Quickstart

Локальные NDJSON fixtures:

- `data/vhod.ndjson`;
- `data/vihod.ndjson`.

Пример использования:

```python
from analyzer import DataLoader, PersonMapper

mapper = PersonMapper("person.json")
df = DataLoader.load_logs(
    ["data/vhod.ndjson", "data/vihod.ndjson"],
    file_type="ndjson",
    person_mapper=mapper,
)
```

`PersonMapper` применяет `aliases`, поэтому дополнительные ID сотрудника нормализуются в основной ID.

Проверка:

```bash
python -m pytest tests/test_mapping_optional.py tests/test_public_api.py
```
