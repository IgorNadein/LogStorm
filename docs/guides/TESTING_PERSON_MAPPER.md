# Тестирование PersonMapper

## Быстрый тест

```bash
# 1. Базовый тест - загрузка с маппингом
python test_ndjson_with_mapper.py

# 2. Интерактивная утилита
python manage_mapping.py

# 3. Примеры использования
python examples_person_mapper.py
```

## Проверка функциональности

### ✅ Тест 1: Маппинг имён
```python
from services import PersonMapper

mapper = PersonMapper('person_mapping.json')

# Проверяем маппинг имени
display_name = mapper.get_display_name('30')
print(display_name)  # Должно быть: "Ирина Погонина"
```

### ✅ Тест 2: Aliases
```python
# Проверяем разрешение alias
resolved = mapper.resolve_person_id('sergei_bondar_2')
print(resolved)  # Должно быть: "54"

# Проверяем получение имени через alias
display = mapper.get_display_name(resolved)
print(display)  # Должно быть: "Сергей Бондарь"
```

### ✅ Тест 3: Расписания
```python
# Проверяем получение расписания
schedule = mapper.get_schedule('3')
print(schedule['start_time'])  # "10:00"
print(schedule['end_time'])    # "19:00"
print(len(schedule['workdays']))  # 4 дня
```

### ✅ Тест 4: Загрузка логов
```python
from services import DataLoader

df = DataLoader.load_logs(
    'LogsCam/vhod.ndjson',
    file_type='ndjson',
    person_mapper=mapper
)

# Проверяем наличие полей
assert 'name' in df.columns
assert 'display_name' in df.columns

# Проверяем маппинг
row = df[df['name'] == '30'].iloc[0]
assert row['display_name'] == 'Ирина Погонина'
```

### ✅ Тест 5: Полный цикл
```python
from services import AttendanceService

# Конвертируем в prefs
prefs = mapper.convert_to_prefs_format()

# Анализируем
service = AttendanceService(df, prefs)
records = service.analyze_all()

# Проверяем
assert len(records) > 0
print(f"✅ Создано {len(records)} записей")
```

## Ожидаемые результаты

После запуска `test_ndjson_with_mapper.py` вы должны увидеть:

```
================================================================================
LogStorm - Тест работы с NDJSON логами СКУД
================================================================================

[1/6] Инициализация PersonMapper...
✅ Загружено 15 маппингов сотрудников

[2/6] Загрузка логов из LogsCam/vhod.ndjson...
Загружено 100 событий из NDJSON
✅ Загружено 85 событий
   Уникальных сотрудников: 15
   Период: 2025-12-01 - 2025-12-31

   📋 Примеры маппинга:
      30                   -> Ирина Погонина
      54                   -> Сергей Бондарь
      3                    -> Эдуард Иванов
      ...

[3/6] Подготовка профилей сотрудников...
✅ Создано 15 профилей из маппинга

[4/6] Анализ посещаемости...
✅ Проанализировано 465 записей

[5/6] Генерация сводки...
[Статистика...]

[6/6] Генерация Excel отчёта...
✅ Excel отчёт сохранён: attendance_report_ndjson.xlsx

================================================================================
✅ Анализ завершён!
================================================================================
```

## Проверка файлов

### person_mapping.json
```bash
# Проверить валидность JSON
python -m json.tool person_mapping.json > /dev/null && echo "✅ JSON валидный"
```

### Excel отчёт
Откройте `attendance_report_ndjson.xlsx` и проверьте:
- [ ] Имена сотрудников отображаются корректно
- [ ] Расписания учтены (время прихода/ухода)
- [ ] Aliases объединены (нет дубликатов)
- [ ] Цветовое кодирование работает

## Отладка

### Проблема: Маппинг не применяется

```python
# Проверьте ID в событии
import json
with open('LogsCam/vhod.ndjson') as f:
    event = json.loads(f.readline())
    print(event.get('employeeNoString'))  # Должен совпадать с ID в маппинге
```

### Проблема: Alias не работает

```python
# Проверьте конфигурацию
mapper = PersonMapper('person_mapping.json')
print(mapper.aliases)  # Должен содержать ваш alias
print(mapper.reverse_alias_map)  # Обратный индекс
```

### Проблема: Расписание не учитывается

```python
# Проверьте профиль
prefs = mapper.convert_to_prefs_format()
print(prefs['30'])  # Должен содержать workdays, start_time, etc.
```

## Производительность

Ожидаемая скорость обработки:
- Загрузка 1000 событий: ~1-2 сек
- Маппинг 1000 событий: ~0.5 сек
- Анализ 30 дней × 20 человек: ~3-5 сек
- Генерация Excel: ~2-3 сек

Итого для типичного месяца: **~10 секунд**
