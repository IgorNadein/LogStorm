# Quickstart

```bash
pip install -r requirements.txt
python -m pytest
python main.py analyze
```

По умолчанию используются:

- CSV: `data/attendance.csv`;
- маппинг: `data/person.sample.json`;
- отчет: `reports/attendance_report.xlsx`.

Пути задаются в `core/settings.py`.

Можно указать collector SQLite базу как источник логов:

```bash
LOGSTORM_LOGS_FILE=events.db python main.py analyze
```

или напрямую:

```python
from analyzer import DataLoader, PersonMapper

mapper = PersonMapper("data/person.sample.json")
df = DataLoader.load_logs("events.db", file_type="sqlite", person_mapper=mapper)
```

GUI удален из active scope. Основной workflow: tests -> `main.py` -> API/collector.
