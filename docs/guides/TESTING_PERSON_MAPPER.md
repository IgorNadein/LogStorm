# Testing PersonMapper

Текущие проверки маппинга:

```bash
python -m pytest tests/test_mapping_optional.py tests/test_melanya_mapping.py
```

Фактические входы:

- `data/person.sample.json`;
- `data/vhod.ndjson`;
- `data/vihod.ndjson`.

Ожидание: ID `666` через aliases нормализуется в основной ID `19`.
