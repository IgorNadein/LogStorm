# Исправление GUI для работы с NDJSON + PersonMapper

## Проблема

GUI приложение (`gui_app.py`) не использовало PersonMapper при загрузке NDJSON файлов, что приводило к невалидным данным:
- Имена не преобразовывались (оставались оригинальные из логов)
- Алиасы не объединялись
- Индивидуальные расписания не применялись

## Исправления

### 1. Добавлены импорты (строки 15-17)
```python
from services import DataLoader, AttendanceService, AIService, PersonMapper
from reporters import SummaryReporter, ExcelReporter, ExcelFormatter
from config import PERSON_MAPPING_FILE
```

### 2. Добавлена переменная для mapping файла (строка 38)
```python
self.mapping_path = tk.StringVar(value=PERSON_MAPPING_FILE)
```

### 3. Добавлена секция UI для маппинга (после строки 221)
```python
# Файл маппинга (для NDJSON)
mapping_frame = ttk.LabelFrame(
    self.setup_tab,
    text="🔄 Файл маппинга сотрудников (для NDJSON)",
    padding=10
)
mapping_frame.pack(fill=tk.X, pady=(0, 10))

ttk.Entry(
    mapping_frame,
    textvariable=self.mapping_path,
    width=60
).pack(side=tk.LEFT, padx=(0, 5))

ttk.Button(
    mapping_frame,
    text="Обзор...",
    command=self._browse_mapping
).pack(side=tk.LEFT)
```

### 4. Добавлен метод выбора файла маппинга (после строки 428)
```python
def _browse_mapping(self):
    """Выбор файла маппинга"""
    filename = filedialog.askopenfilename(
        title="Выберите файл маппинга (person_mapping.json)",
        filetypes=FILE_TYPES_JSON,
        initialdir="."
    )
    if filename:
        self.mapping_path.set(filename)
        self._log(f"✅ Выбран файл маппинга: {filename}")
```

### 5. Обновлена логика загрузки данных (метод _run_analysis)

#### До:
```python
# Загрузка профилей (опционально)
prefs_path = self.prefs_path.get()
if prefs_path:
    prefs = DataLoader.load_preferences(prefs_path)
else:
    prefs = {}
```

#### После:
```python
# Загрузка PersonMapper для NDJSON (опционально)
person_mapper = None
mapping_path = self.mapping_path.get()
if mapping_path and os.path.exists(mapping_path):
    try:
        person_mapper = PersonMapper(mapping_path)
        self._log(f"✅ Загружен маппинг: {mapping_path}")
        self._log(f"   Сотрудников: {len(person_mapper.mappings)}")
        self._log(f"   Алиасов: {len(person_mapper.aliases)}")
    except Exception as e:
        self._log(f"⚠️ Ошибка загрузки маппинга: {e}")
        person_mapper = None

# Передаём маппер в DataLoader
df = DataLoader.load_logs(
    self.logs_paths[0],
    file_type=self.file_type.get(),
    person_mapper=person_mapper  # ← Добавлено!
)

# Загрузка профилей (опционально)
prefs_path = self.prefs_path.get()
if prefs_path and os.path.exists(prefs_path):
    prefs = DataLoader.load_preferences(prefs_path)
else:
    # Если есть маппер, конвертируем его в формат prefs
    if person_mapper:
        prefs = person_mapper.convert_to_prefs_format()
        self._log("✅ Расписания загружены из маппинга")
    else:
        prefs = {}
```

## Результат

Теперь GUI корректно обрабатывает NDJSON файлы:

### Пример работы:

**NDJSON (исходник):**
```json
{"name": "Серёга Бондарь", "employeeNoString": "54", "time": "2025-12-16T18:04:40+03:00"}
```

**person_mapping.json:**
```json
{
  "person_mappings": {
    "54": {
      "display_name": "Сергей Бондарь",
      "original_names": ["Серёга Бондарь"],
      "workdays": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
      "start_time": "09:00",
      "end_time": "18:00",
      "work_hours": 9
    }
  }
}
```

**Результат в отчёте:**
- Имя: **Сергей Бондарь** (вместо "Серёга Бондарь")
- Расписание: Пн-Пт, 09:00-18:00, 9 часов
- Все проблемы учитывают индивидуальное расписание

## Тестирование

Запустите тест:
```bash
python test_gui_ndjson.py
```

Ожидаемый результат:
```
✅ Импорты
✅ PersonMapper
✅ DataLoader+Mapper
✅ Конвертация в prefs

Пройдено: 4/4
```

## Использование GUI

1. Запустите GUI:
   ```bash
   python gui_app.py
   ```

2. Вкладка "⚙️ Настройки":
   - Добавьте NDJSON файлы (vhod.ndjson, vihod.ndjson)
   - Укажите person_mapping.json в поле "Файл маппинга"
   - Запустите анализ

3. Проверьте лог во вкладке "📊 Анализ":
   ```
   ✅ Загружен маппинг: person_mapping.json
      Сотрудников: 15
      Алиасов: 2
   ✅ Загружено 3524 записей, 15 профилей
   ✅ Расписания загружены из маппинга
   ```

## Документация

Созданные гайды:
- `GUI_NDJSON_GUIDE.md` - Полное руководство по работе с GUI + NDJSON
- `NDJSON_MAPPING_GUIDE.md` - Детальное описание PersonMapper
- `QUICKSTART_NDJSON.md` - Быстрый старт

## См. также

- `manage_mapping.py` - Интерактивное управление person_mapping.json
- `test_ndjson_with_mapper.py` - Тест полного workflow
- `examples_person_mapper.py` - Примеры использования API
