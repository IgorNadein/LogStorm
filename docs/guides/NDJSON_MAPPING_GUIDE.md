# Руководство по работе с NDJSON логами СКУД

## Обзор

Система LogStorm теперь поддерживает работу с логами систем контроля доступа (СКУД) в формате NDJSON, включая возможности:

1. **Маппинг имён** - изменение отображаемых имён сотрудников
2. **Индивидуальные расписания** - настройка рабочих дней и часов для каждого сотрудника
3. **Объединение ID (aliases)** - учёт нескольких ID как одного человека

## Формат NDJSON логов

Пример события из системы Hikvision:

```json
{
  "major": 5,
  "minor": 75,
  "time": "2025-12-01T08:48:56+03:00",
  "cardNo": "18446744073609551895",
  "cardType": 1,
  "name": "Ирина Погонина",
  "cardReaderNo": 1,
  "doorNo": 1,
  "employeeNoString": "30",
  "serialNo": 97800,
  "userType": "normal",
  "currentVerifyMode": "cardOrFace",
  "mask": "unknown",
  "pictureURL": "http://192.168.1.101/LOCALS/pic/...",
  "FaceRect": {"height": 0.057, "width": 0.032, "x": 0.565, "y": 0.492}
}
```

## Файл конфигурации `person_mapping.json`

### Структура файла

```json
{
  "person_mappings": {
    "ID_сотрудника": {
      "display_name": "Отображаемое имя",
      "original_names": ["Имя 1 из СКУД", "Имя 2 из СКУД"],
      "workdays": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
      "start_time": "09:00",
      "end_time": "18:00",
      "work_hours": 9
    }
  },
  "aliases": {
    "главный_ID": ["дополнительный_ID_1", "дополнительный_ID_2"]
  }
}
```

### Поля конфигурации

#### person_mappings

| Поле | Описание | Обязательное |
|------|----------|--------------|
| `display_name` | Имя для отображения в отчётах | Да |
| `original_names` | Список возможных имён из СКУД | Нет |
| `workdays` | Рабочие дни недели | Нет (по умолчанию Пн-Пт) |
| `start_time` | Время начала работы (HH:MM) | Нет (по умолчанию 09:00) |
| `end_time` | Время окончания работы (HH:MM) | Нет (по умолчанию 18:00) |
| `work_hours` | Часов работы в день | Нет (по умолчанию 9) |

#### aliases

Позволяет объединить несколько ID в одного человека. Это полезно когда:
- У сотрудника несколько карт доступа
- Было изменение ID в системе
- Разные системы используют разные идентификаторы

## Примеры использования

### 1. Базовый маппинг с изменением имени

```json
{
  "person_mappings": {
    "30": {
      "display_name": "Ирина Погонина",
      "original_names": ["Ирина Погонина"],
      "workdays": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
      "start_time": "09:00",
      "end_time": "18:00",
      "work_hours": 9
    }
  }
}
```

### 2. Сотрудник с индивидуальным графиком

```json
{
  "person_mappings": {
    "3": {
      "display_name": "Эдуард Employee Sample",
      "original_names": ["Эдуард Employee Sample"],
      "workdays": ["Monday", "Tuesday", "Wednesday", "Thursday"],
      "start_time": "10:00",
      "end_time": "19:00",
      "work_hours": 9
    }
  }
}
```

### 3. Объединение нескольких вариантов имени

```json
{
  "person_mappings": {
    "55": {
      "display_name": "Employee Delta",
      "original_names": [
        "Employee Delta",
        "Employee Delta",
        "Employee Delta"
      ],
      "workdays": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
      "start_time": "09:00",
      "end_time": "18:00",
      "work_hours": 9
    }
  }
}
```

### 4. Использование aliases (несколько ID = один человек)

```json
{
  "person_mappings": {
    "54": {
      "display_name": "Сергей Бондарь",
      "original_names": ["Серёга Бондарь", "Сергей Бондарь"],
      "workdays": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
      "start_time": "08:00",
      "end_time": "17:00",
      "work_hours": 9
    }
  },
  "aliases": {
    "54": ["sergei_bondar_2", "bondar_sergey"]
  }
}
```

В этом примере все события с ID `54`, `sergei_bondar_2` и `bondar_sergey` будут учитываться как события одного человека - "Сергей Бондарь".

## Запуск анализа

### Тестовый скрипт

```bash
python test_ndjson_with_mapper.py
```

Этот скрипт:
1. Загружает конфигурацию из `person_mapping.json`
2. Читает NDJSON логи из `LogsCam/vhod.ndjson`
3. Применяет маппинг и объединяет aliases
4. Анализирует посещаемость
5. Генерирует Excel отчёт

### Программное использование

```python
from services import DataLoader, PersonMapper, AttendanceService

# 1. Инициализация маппера
person_mapper = PersonMapper('person_mapping.json')

# 2. Загрузка логов с маппингом
df = DataLoader.load_logs(
    'LogsCam/vhod.ndjson',
    file_type='ndjson',
    person_mapper=person_mapper
)

# 3. Подготовка профилей
prefs = person_mapper.convert_to_prefs_format()

# 4. Анализ
service = AttendanceService(df, prefs)
records = service.analyze_all()
```

## Добавление нового сотрудника программно

```python
from services import PersonMapper

mapper = PersonMapper('person_mapping.json')

# Добавить нового сотрудника
mapper.add_person(
    person_id='99',
    display_name='Employee Sample',
    original_names=['Employee Sample', 'И. Employee Sample'],
    workdays=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
    start_time='09:00',
    end_time='18:00',
    work_hours=9
)

# Добавить alias
mapper.add_alias(
    main_id='99',
    alias_ids=['ivan_99', 'ivanov_ivan']
)

# Сохранить изменения
mapper.save_mappings()
```

## Работа с несколькими файлами

```python
from services import DataLoader, PersonMapper

person_mapper = PersonMapper('person_mapping.json')

# Загрузить несколько файлов одновременно
files = [
    'LogsCam/vhod.ndjson',
    'LogsCam/vihod.ndjson',
    'LogsCam/events.ndjson'
]

df = DataLoader.load_logs(
    files,
    file_type='ndjson',
    person_mapper=person_mapper
)
```

## Проверка маппинга

После загрузки логов можно проверить, как применился маппинг:

```python
# Показать уникальные пары ID -> Отображаемое имя
unique_persons = df[['name', 'display_name']].drop_duplicates()
print(unique_persons)
```

## Отладка

Если маппинг не применяется:

1. **Проверьте ID** - используется `employeeNoString` из NDJSON
2. **Проверьте имена** - должны точно совпадать с `original_names`
3. **Проверьте aliases** - убедитесь, что главный ID существует в `person_mappings`

```python
# Проверить, как определяется ID для события
event = {
    'employeeNoString': '30',
    'name': 'Ирина Погонина'
}

person_id, display_name = person_mapper.process_event(event)
print(f"ID: {person_id}, Имя: {display_name}")
```

## Рекомендации

1. **Используйте employeeNoString как ID** - это стабильный идентификатор
2. **Добавляйте все варианты имён** в `original_names` для надёжности
3. **Группируйте сотрудников по расписанию** - проще копировать конфигурацию
4. **Используйте aliases осторожно** - убедитесь, что действительно один человек
5. **Делайте бэкапы** `person_mapping.json` перед большими изменениями

## Структура проекта

```
LogStorm/
├── person_mapping.json          # Конфигурация маппинга
├── test_ndjson_with_mapper.py   # Тестовый скрипт
├── services/
│   ├── person_mapper.py         # Класс PersonMapper
│   ├── logscam_loader.py        # Загрузчик NDJSON
│   └── data_loader.py           # Универсальный загрузчик
└── LogsCam/
    ├── vhod.ndjson              # Логи входов
    ├── vihod.ndjson             # Логи выходов
    └── events.ndjson            # Все события
```

## Типичные задачи

### Переименовать сотрудника

Отредактируйте `display_name` в `person_mapping.json`:

```json
"30": {
  "display_name": "Ирина Александровна Погонина",
  ...
}
```

### Изменить расписание

```json
"3": {
  "display_name": "Эдуард Employee Sample",
  "workdays": ["Monday", "Tuesday", "Wednesday", "Thursday"],
  "start_time": "10:00",
  "end_time": "19:00",
  "work_hours": 9
}
```

### Объединить двух сотрудников

Если выяснилось, что ID "54" и "54_old" - это один человек:

```json
{
  "person_mappings": {
    "54": {
      "display_name": "Сергей Бондарь",
      ...
    }
  },
  "aliases": {
    "54": ["54_old"]
  }
}
```

## Отчёты

После анализа создаются:

1. **attendance_report_ndjson.xlsx** - детальный Excel отчёт:
   - Лист "Отчет по дням" - посещаемость по дням
   - Лист "Подозрительные случаи" - технические сбои
   - Листы по месяцам - сводка по месяцам

2. **Консольный вывод** - статистика и топы:
   - Топ опозданий
   - Топ переработок
   - Массовые отсутствия
   - Технические проблемы

## Поддержка

При возникновении проблем:

1. Проверьте формат NDJSON файла
2. Проверьте синтаксис `person_mapping.json` (валидный JSON)
3. Проверьте наличие поля `employeeNoString` или `name` в событиях
4. Используйте режим отладки для проверки маппинга
