# Changelog v2.8 - PersonMapper для СКУД

## 🎉 Новые возможности

### PersonMapper - Система маппинга сотрудников из СКУД

Добавлена полноценная система для работы с логами систем контроля доступа (СКУД) в формате NDJSON.

#### Основные возможности:

1. **Маппинг имён сотрудников** 
   - Изменение отображаемых имён в отчётах
   - Поддержка нескольких вариантов написания имени из СКУД
   - Автоматическое сопоставление по ID или имени

2. **Индивидуальные расписания**
   - Настройка рабочих дней для каждого сотрудника
   - Индивидуальное время начала и окончания работы
   - Различное количество рабочих часов (4, 6, 8, 9 часов и т.д.)

3. **Aliases - объединение нескольких ID**
   - Учёт нескольких ID как одного человека
   - Полезно при смене карт доступа или изменении ID в системе
   - Автоматическое разрешение главного ID

## 📁 Новые файлы

### Основные модули:
- `services/person_mapper.py` - Класс PersonMapper для маппинга сотрудников
- `person_mapping.json` - Файл конфигурации маппинга (пример)

### Утилиты и тесты:
- `manage_mapping.py` - Интерактивная утилита управления маппингом
- `test_ndjson_with_mapper.py` - Тестовый скрипт для работы с NDJSON
- `examples_person_mapper.py` - Примеры использования всех возможностей

### Документация:
- `QUICKSTART_NDJSON.md` - Быстрый старт для работы с NDJSON логами
- `NDJSON_MAPPING_GUIDE.md` - Полное руководство по маппингу

## 🔧 Изменения в существующих модулях

### `services/logscam_loader.py`
- ✅ Добавлен параметр `person_mapper` в методы загрузки
- ✅ Автоматическое применение маппинга при загрузке событий
- ✅ Извлечение как `person_id`, так и `display_name`

### `services/data_loader.py`
- ✅ Поддержка `person_mapper` во всех методах загрузки
- ✅ Передача маппера в `LogsCamLoader`
- ✅ Работа с одиночными и множественными файлами

### `services/__init__.py`
- ✅ Экспорт `PersonMapper` для удобного импорта

### `config.py`
- ✅ Добавлена константа `PERSON_MAPPING_FILE`

### `README.md`
- ✅ Обновлена версия до v2.8
- ✅ Добавлено описание PersonMapper
- ✅ Ссылки на новую документацию

## 📋 Структура person_mapping.json

```json
{
  "person_mappings": {
    "ID_сотрудника": {
      "display_name": "Отображаемое Имя",
      "original_names": ["Вариант 1", "Вариант 2"],
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

## 💻 Примеры использования

### Базовая загрузка с маппингом:

```python
from services import DataLoader, PersonMapper

# Инициализация маппера
mapper = PersonMapper('person_mapping.json')

# Загрузка логов с применением маппинга
df = DataLoader.load_logs(
    'LogsCam/vhod.ndjson',
    file_type='ndjson',
    person_mapper=mapper
)

# В DataFrame будут поля:
# - name: person_id (главный ID с учётом aliases)
# - display_name: отображаемое имя
```

### Добавление нового сотрудника:

```python
mapper = PersonMapper('person_mapping.json')

mapper.add_person(
    person_id='99',
    display_name='Иван Иванов',
    original_names=['Иван Иванов', 'И. Иванов'],
    workdays=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
    start_time='09:00',
    end_time='18:00',
    work_hours=9
)

mapper.save_mappings()
```

### Объединение нескольких ID:

```python
mapper = PersonMapper('person_mapping.json')

# Все события с ID 54, old_54, new_54 будут учитываться как один человек
mapper.add_alias(
    main_id='54',
    alias_ids=['old_54', 'new_54']
)

mapper.save_mappings()
```

## 🛠️ Интерактивная утилита

Запустите для удобного управления маппингом:

```bash
python manage_mapping.py
```

Возможности:
1. Просмотр всех сотрудников
2. Добавление нового сотрудника
3. Редактирование существующего
4. Добавление aliases
5. Просмотр всех aliases
6. Импорт из NDJSON файла
7. Экспорт в person_prefs.json

## 🚀 Быстрый старт

1. Поместите NDJSON файлы в `LogsCam/`
2. Запустите тестовый скрипт:
   ```bash
   python test_ndjson_with_mapper.py
   ```
3. Настройте маппинг при необходимости:
   ```bash
   python manage_mapping.py
   ```

## 📖 Документация

- **Быстрый старт**: `QUICKSTART_NDJSON.md`
- **Полное руководство**: `NDJSON_MAPPING_GUIDE.md`
- **Примеры кода**: `examples_person_mapper.py`

## 🔄 Обратная совместимость

✅ Все изменения полностью обратно совместимы:
- Если не передавать `person_mapper` - работает как раньше
- Старые скрипты продолжают работать без изменений
- CSV логи работают как и прежде

## 🎯 Сценарии использования

### 1. Компания с СКУД Hikvision
- Экспортируйте события в NDJSON
- Настройте маппинг для изменения имён
- Получите читаемые отчёты на русском

### 2. Разные графики работы
- Настройте индивидуальные расписания
- Часть сотрудников работает 4 дня, часть 5
- Разное время начала работы (кто-то с 8:00, кто-то с 10:00)

### 3. Смена карт доступа
- Используйте aliases для объединения старых и новых ID
- История посещаемости сохраняется при смене карты
- Один сотрудник в отчёте, даже если менял ID

### 4. Миграция из старой системы
- Импортируйте всех сотрудников автоматически
- Настройте отображаемые имена
- Объедините дубликаты через aliases

## 🐛 Исправления

- Улучшена обработка событий без `employeeNoString`
- Корректная работа с пустыми именами в NDJSON
- Исправлены предупреждения линтера

## ⚠️ Известные ограничения

- Aliases работают только на уровне ID, не имён
- При конфликте ID приоритет у маппинга, а не у NDJSON
- Максимальная вложенность aliases: 1 уровень (нет цепочек)

## 🔮 Планы на будущее

- [ ] GUI для управления маппингом
- [ ] Импорт маппинга из Excel
- [ ] Автоматическое обнаружение дубликатов по имени
- [ ] История изменений маппинга
- [ ] Валидация маппинга перед применением

## 👥 Для разработчиков

### API PersonMapper:

```python
class PersonMapper:
    def resolve_person_id(self, employee_id, name=None) -> str
    def get_display_name(self, person_id) -> str
    def get_schedule(self, person_id) -> Dict
    def process_event(self, event) -> Tuple[str, str]
    def add_person(...) -> bool
    def add_alias(main_id, alias_ids) -> bool
    def save_mappings() -> bool
    def convert_to_prefs_format() -> Dict
```

### Интеграция в существующий код:

```python
# До:
df = DataLoader.load_logs('logs.ndjson', file_type='ndjson')

# После:
mapper = PersonMapper('person_mapping.json')
df = DataLoader.load_logs('logs.ndjson', file_type='ndjson', 
                         person_mapper=mapper)
```

---

**Дата релиза**: Декабрь 2025  
**Версия**: 2.8.0  
**Автор**: LogStorm Team
