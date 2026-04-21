# Quickstart

```bash
pip install -r requirements.txt
python -m pytest
python main.py
```

По умолчанию используются:

- CSV: `data/attendance.csv`;
- маппинг: `person.json`;
- отчет: `reports/attendance_report.xlsx`.

Пути задаются в `config/paths.py`.

Можно указать collector SQLite базу как источник логов:

```python
# config/paths.py
logs_file = "events.db"
```

или напрямую:

```python
from services import DataLoader, PersonMapper

mapper = PersonMapper("person.json")
df = DataLoader.load_logs("events.db", file_type="sqlite", person_mapper=mapper)
```

GUI сейчас заморожен. Основной workflow: tests -> CLI/core -> collector.
