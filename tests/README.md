# LogStorm Tests

Набор тестов для проверки функциональности LogStorm.

## 🧪 Актуальные тесты

### `test_mapping_optional.py`
Проверяет работу aliases (объединение дублирующих ID):
- БЕЗ person_mapping.json: каждый ID остается отдельным
- С person_mapping.json: ID объединяются через aliases

**Запуск:**
```bash
python tests/test_mapping_optional.py
```

### `test_melanya_mapping.py`
Тест конкретного кейса объединения ID "666" и "19" для "Меланя Гаспарян".

**Запуск:**
```bash
python tests/test_melanya_mapping.py
```

### `test_ndjson_with_mapper.py`
Проверяет загрузку NDJSON файлов с применением PersonMapper.

**Запуск:**
```bash
python tests/test_ndjson_with_mapper.py
```

## ▶️ Запуск всех тестов

```bash
# Из корневой директории проекта
python -m pytest tests/ -v

# Или запустить каждый тест отдельно
python tests/test_mapping_optional.py
python tests/test_melanya_mapping.py
python tests/test_ndjson_with_mapper.py
```

## 📋 Что тестируется

- ✅ Загрузка NDJSON файлов из СКУД систем
- ✅ Работа PersonMapper с aliases
- ✅ Объединение дублирующих ID сотрудников
- ✅ Корректность маппинга имен и расписаний
- ✅ Фильтрация только валидных событий (major=5, minor=75)

## 🔧 Требования

Тесты используют реальные данные из директории `LogsCam/`:
- `vhod.ndjson` - входы
- `vihod.ndjson` - выходы

А также конфигурационный файл:
- `person_mapping.json` - маппинг сотрудников
