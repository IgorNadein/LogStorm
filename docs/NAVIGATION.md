# 🧭 Навигация по проекту LogStorm

## 🚀 Быстрый старт

```bash
# Запуск GUI
python run_gui.py

# Запуск CLI
python main.py
```

---

## 📂 Основные файлы

| Файл | Описание |
|------|----------|
| `run_gui.py` | 🖥️ Запуск GUI приложения |
| `main.py` | ⌨️ CLI интерфейс |
| `gui_app_fluent.py` | 🎨 GUI код (Windows 11 Fluent) |
| `config.py` | ⚙️ Настройки системы |
| `config.json` | 👤 Настройки пользователя |
| `person_mapping.json` | 👥 База сотрудников |

---

## 📚 Документация

### Руководства (`docs/guides/`)
- **Быстрый старт**: `QUICKSTART.md`
- **GUI гайд**: `FLUENT_GUI_GUIDE.md`
- **Настройки**: `THRESHOLDS_CONFIG.md`
- **Конфигурация**: `CONFIGURATION_GUIDE.md`
- **NDJSON**: `NDJSON_MAPPING_GUIDE.md`
- **Безопасность**: `SECURITY.md`

### История (`docs/changelogs/`)
- **Changelog**: `CHANGELOG.md`
- **v2.8**: `CHANGELOG_v2.8.md`
- **GUI v2.9.3**: `GUI_UPDATES_v2.9.3.md`

### Исправления (`docs/fixes/`)
- **Выходные дни**: `WEEKEND_LOGIC_FIX.md`
- **Рефакторинг**: `REFACTORING_*.md`
- **NDJSON**: `GUI_NDJSON_FIX.md`

---

## 🗂️ Структура кода

| Папка | Содержимое |
|-------|-----------|
| `analyzers/` | 🔍 Анализаторы (статусы, технические сбои) |
| `models/` | 📊 Модели данных (записи, графики) |
| `services/` | ⚡ Бизнес-логика (AI, загрузка, маппинг) |
| `reporters/` | 📄 Генерация отчетов (Excel, форматирование) |
| `validators/` | ✅ Валидаторы (время, отсутствия) |
| `utils/` | 🛠️ Утилиты (даты, события, Excel) |
| `tools/` | 🔧 CLI утилиты |
| `tests/` | 🧪 Тесты |

---

## 🗄️ Архив

| Папка | Содержимое |
|-------|-----------|
| `archive/old_gui/` | Старые версии GUI (6 файлов) |
| `archive/old_tests/` | Устаревшие тесты (5 файлов) |
| `archive/` | Старые конфиги (4 файла) |

---

## ⚙️ Конфигурация

### Пороговые значения (`config.py`)
```python
LATE_THRESHOLD_MINUTES = 15      # Опоздание
OVERTIME_THRESHOLD = 10          # Переработка
CRITICAL_LATE_MINUTES = 180      # Критическое опоздание
CRITICAL_UNDERWORK_HOURS = 7     # Критическая недоработка
NIGHT_HOUR_START = 23            # Ночь (начало)
NIGHT_HOUR_END = 3               # Ночь (конец)
```

### Сотрудники (`person_mapping.json`)
```json
{
  "person_mappings": {
    "ID": {
      "display_name": "Имя",
      "workdays": ["Monday", ...],
      "start_time": "09:00",
      "end_time": "18:00"
    }
  },
  "aliases": {
    "MainID": ["AliasID1", ...]
  }
}
```

---

## 🎯 Типичные задачи

### Добавить сотрудника
1. GUI → вкладка "Сотрудники" → "Добавить"
2. Или редактировать `person_mapping.json`

### Загрузить логи
1. GUI → вкладка "Логи"
2. Указать IP устройства, даты
3. "Получить логи"

### Проанализировать
1. GUI → вкладка "Анализ"
2. "Запустить анализ"

### Экспортировать отчет
1. GUI → вкладка "Экспорт"
2. "Экспортировать"

---

## 🔍 Поиск информации

**Нужно**|**Смотри**
---------|----------
Запустить проект | `run_gui.py` или `main.py`
Настроить пороги | `config.py` + `docs/guides/THRESHOLDS_CONFIG.md`
Добавить людей | `person_mapping.json` + GUI
Понять структуру | `PROJECT_STRUCTURE.md`
История изменений | `docs/changelogs/`
Исправления багов | `docs/fixes/`
Старый код | `archive/`

---

## 📖 Полная документация

- **Структура**: `PROJECT_STRUCTURE.md` (детальное описание всех папок)
- **Рефакторинг**: `.refactoring_summary.md` (отчет о рефакторинге)
- **Готово**: `REFACTORING_DONE.md` (итоги рефакторинга)

---

**Версия**: 2.9.3+  
**Дата**: 22.12.2025  
**Статус**: ✅ Рефакторинг завершен
