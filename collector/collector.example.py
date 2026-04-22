"""Example LogStorm collector configuration.

Copy this file to ``collector.local.py`` and keep real credentials out of Git.
The collector expects a top-level ``CONFIG`` dictionary.
"""

CONFIG = {
    "storage": {
        "ndjson": "events.ndjson",
        "sqlite": "events.db",
    },
    "log_file": "collector.log",
    "interval_minutes": 15,
    "max_parallel": 4,
    "initial_days": 30,
    "images": {
        "enabled": False,
        "folder": "images",
        "format": "{date}/{employeeNoString}_{serialNo}.jpg",
    },
    "devices": [
        {
            "name": "Камера входа",
            "host": "192.168.1.101",
            "user": "admin",
            "password": "CHANGE_ME",
            "enabled": True,
        },
        {
            "name": "Камера выхода",
            "host": "192.168.1.102",
            "user": "admin",
            "password": "CHANGE_ME",
            "enabled": True,
        },
    ],
    "request": {
        "page_size": 30,
        "timeout": 180,
        "retries": 3,
        "major": 5,
        "minor": 0,
    },
}
