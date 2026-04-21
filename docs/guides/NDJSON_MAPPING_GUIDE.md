# NDJSON Mapping Guide

Актуальный файл маппинга: `person.json`.

Минимальный формат:

```json
{
  "person_mappings": {
    "19": {
      "display_name": "Имя Фамилия",
      "workdays": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
      "start_time": "08:00",
      "work_hours": 9
    }
  },
  "aliases": {
    "19": ["666"]
  }
}
```

Проверяемый сценарий:

```python
from services import DataLoader, PersonMapper

mapper = PersonMapper("person.json")
df = DataLoader.load_logs(
    ["data/vhod.ndjson", "data/vihod.ndjson"],
    file_type="ndjson",
    person_mapper=mapper,
)
```

Без маппера ID остаются отдельными. С маппером aliases объединяются в основной ID. Это закреплено в `tests/test_mapping_optional.py`.
