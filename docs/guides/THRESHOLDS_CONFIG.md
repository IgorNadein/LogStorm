# Thresholds Config

Пороги анализа находятся в `config/analysis.py`.

Текущие значения:

- `late_threshold_minutes = 5`;
- `overtime_threshold = 10`;
- `critical_late_minutes = 180`;
- `critical_underwork_hours = 3`;
- `night_hour_start = 23`;
- `night_hour_end = 3`.

Проверка:

```bash
python -m pytest tests/test_config.py
```

При изменении порогов обновляйте тестовые ожидания только если новое значение является осознанным продуктовым решением.
