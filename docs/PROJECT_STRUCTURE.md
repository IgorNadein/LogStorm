# 📁 Структура проекта LogStorm

## 🎯 Корневые файлы

### Точки входа
- **`run_gui.py`** - Запуск GUI приложения (рекомендуемый способ)
- **`main.py`** - CLI версия для командной строки
- **`gui_app_fluent.py`** - Основной GUI модуль (Windows 11 Fluent Design)

### Конфигурация
- **`config.py`** - Основные настройки (пороговые значения, цвета, константы)
- **`config.json`** - Пользовательские настройки GUI (файлы, пути)
- **`person_mapping.json`** - База данных сотрудников с графиками работы
- **`requirements.txt`** - Зависимости Python
- **`setup.py`** - Установка пакета

### Документация
- **`README.md`** - Основная документация проекта
- **`PROJECT_STRUCTURE.md`** - Этот файл (структура проекта)

### Окружение
- **`.env`** - Локальные переменные окружения (не в git)
- **`.env.example`** - Пример файла окружения
- **`.gitignore`** - Игнорируемые git файлы

---

## 📂 Папки

### `analyzers/` - Анализаторы данных
```
analyzers/
├── __init__.py
├── status_analyzer.py        # Анализ статусов (опоздания, переработки)
└── technical_analyzer.py     # Определение технических сбоев
```

### `models/` - Модели данных
```
models/
├── __init__.py
├── attendance_record.py      # Модель записи посещения
└── work_schedule.py           # Модель графика работы
```

### `services/` - Бизнес-логика
```
services/
├── __init__.py
├── ai_service.py              # AI анализ (GigaChat)
├── attendance_service.py      # Обработка посещаемости
├── data_loader.py             # Загрузка данных из файлов
├── logscam_loader.py          # Загрузка NDJSON логов
└── person_mapper.py           # Маппинг сотрудников и алиасов
```

### `reporters/` - Генерация отчетов
```
reporters/
├── __init__.py
├── excel_formatter.py         # Форматирование Excel (цвета)
├── excel_reporter.py          # Генерация Excel отчетов
└── summary_reporter.py        # Текстовые отчеты
```

### `validators/` - Валидаторы
```
validators/
├── __init__.py
├── absence_validator.py       # Проверка массовых отсутствий
└── time_validator.py          # Валидация временных данных
```

### `utils/` - Утилиты
```
utils/
├── __init__.py
├── date_utils.py              # Работа с датами
├── event_mapper.py            # Маппинг событий
└── excel_utils.py             # Excel утилиты
```

### `tools/` - Вспомогательные скрипты
```
tools/
├── cli.py                     # CLI интерфейс
├── app.py                     # Дополнительный CLI
├── manage_mapping.py          # Управление маппингом
└── export/                    # Утилиты экспорта
    └── EXPORT_GUIDE.md
```

### `tests/` - Тесты
```
tests/
├── __init__.py
└── test_weekend_logic.py      # Тест логики выходных дней
```

### `docs/` - Документация

#### `docs/guides/` - Руководства
```
docs/guides/
├── ANALYSIS_CONFIG_GUIDE.md          # Настройка анализа
├── CHEATSHEET.md                     # Шпаргалка команд
├── CONFIGURATION_GUIDE.md            # Руководство по конфигурации
├── FLUENT_GUI_GUIDE.md               # Гайд по Fluent GUI
├── FORMATTING_RULES_GUIDE.md         # Правила форматирования
├── GUI_GUIDE.md                      # Основное руководство GUI
├── GUI_NDJSON_GUIDE.md               # Работа с NDJSON в GUI
├── GUI_PERSON_MANAGER_GUIDE.md       # Управление сотрудниками
├── NDJSON_MAPPING_GUIDE.md           # Маппинг NDJSON данных
├── QUICKSTART.md                     # Быстрый старт
├── QUICKSTART_NDJSON.md              # Быстрый старт с NDJSON
├── QUICK_CONFIG.md                   # Быстрая настройка
├── SECURITY.md                       # Безопасность
├── TESTING_PERSON_MAPPER.md          # Тестирование маппера
└── THRESHOLDS_CONFIG.md              # Настройка пороговых значений
```

#### `docs/changelogs/` - История изменений
```
docs/changelogs/
├── CHANGELOG.md                      # Основной changelog
├── CHANGELOG_v2.8.md                 # Изменения v2.8
└── GUI_UPDATES_v2.9.3.md             # Обновления GUI v2.9.3
```

#### `docs/fixes/` - Документация исправлений
```
docs/fixes/
├── FIX_SUMMARY.md                    # Сводка исправлений
├── GUI_NDJSON_CHECKLIST.md           # Чеклист NDJSON
├── GUI_NDJSON_FIX.md                 # Исправление NDJSON
├── REFACTORING_AUDIT.md              # Аудит рефакторинга
├── REFACTORING_COMPLETE.md           # Завершение рефакторинга
├── REFACTORING_PERSONMAPPER.md       # Рефакторинг маппера
├── REFACTORING_REPORT_v3.0.md        # Отчет рефакторинга v3.0
└── WEEKEND_LOGIC_FIX.md              # Исправление логики выходных
```

### `archive/` - Архив старых файлов

#### `archive/old_gui/` - Старые версии GUI
```
archive/old_gui/
├── gui_app.py                        # Первая версия GUI
├── gui_app_qt.py                     # Qt версия
├── gui_app_qt_new.py                 # Новая Qt версия
├── gui_config.py                     # Старый конфиг GUI
├── gui_export_logs.py                # Старый экспорт
└── gui_person_manager.py             # Старый менеджер
```

#### `archive/old_tests/` - Устаревшие тесты
```
archive/old_tests/
├── test_event_merging.py
├── test_gui_ndjson.py
├── test_mapping_optional.py
├── test_melanya_mapping.py
└── test_ndjson_with_mapper.py
```

#### `archive/` - Прочие архивные файлы
```
archive/
├── analysis_config.py                # Старый конфиг анализа
├── demo_config.py                    # Демо конфиг
├── refactor.py                       # Скрипт рефакторинга
└── examples_person_mapper.py         # Примеры маппера
```

### `data/` - Данные для тестов
### `path/` - Временные пути
### `reports/` - Сгенерированные отчеты
### `LogsCam/` - Данные с камер
### `refactoring_backup/` - Бэкапы рефакторинга

---

## 🚀 Быстрый старт

### 1. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 2. Запуск GUI
```bash
python run_gui.py
```

### 3. Запуск CLI
```bash
python main.py --help
```

---

## 📝 Основные файлы для работы

### Для пользователей:
1. **`run_gui.py`** - запуск приложения
2. **`person_mapping.json`** - настройка сотрудников
3. **`config.json`** - настройки приложения
4. **`docs/guides/QUICKSTART.md`** - руководство

### Для разработчиков:
1. **`config.py`** - настройка пороговых значений
2. **`docs/guides/THRESHOLDS_CONFIG.md`** - описание настроек
3. **`PROJECT_STRUCTURE.md`** - структура проекта
4. **`docs/fixes/`** - история исправлений

---

## 🔧 Конфигурация

### Пороговые значения (`config.py`)
- Опоздания: `LATE_THRESHOLD_MINUTES = 15`
- Переработки: `OVERTIME_THRESHOLD = 10`
- Критические сбои: `CRITICAL_LATE_MINUTES = 180`
- И другие настройки...

### Сотрудники (`person_mapping.json`)
```json
{
  "person_mappings": {
    "ID": {
      "display_name": "Имя Фамилия",
      "workdays": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
      "start_time": "09:00",
      "end_time": "18:00",
      "work_hours": 9
    }
  },
  "aliases": {
    "MainID": ["AliasID1", "AliasID2"]
  }
}
```

---

## 📊 Типичный workflow

1. **Настройка сотрудников** → `person_mapping.json`
2. **Загрузка логов** → GUI вкладка "Логи"
3. **Настройка параметров** → GUI вкладка "Настройки"
4. **Анализ** → GUI вкладка "Анализ"
5. **Экспорт отчета** → GUI вкладка "Экспорт"

---

## 🛠️ Архитектура

```
┌─────────────────┐
│   GUI / CLI     │
└────────┬────────┘
         │
┌────────▼────────┐
│    Services     │ ◄── AI Service, PersonMapper
└────────┬────────┘
         │
┌────────▼────────┐
│   Analyzers     │ ◄── Status, Technical
└────────┬────────┘
         │
┌────────▼────────┐
│   Validators    │ ◄── Time, Absence
└────────┬────────┘
         │
┌────────▼────────┐
│    Reporters    │ ◄── Excel, Summary
└─────────────────┘
```

---

## 📚 Дополнительная документация

- **Быстрый старт**: `docs/guides/QUICKSTART.md`
- **GUI**: `docs/guides/FLUENT_GUI_GUIDE.md`
- **Настройки**: `docs/guides/THRESHOLDS_CONFIG.md`
- **NDJSON**: `docs/guides/NDJSON_MAPPING_GUIDE.md`
- **Безопасность**: `docs/guides/SECURITY.md`

---

**Версия документа**: 1.0  
**Дата**: 22.12.2025  
**Проект**: LogStorm - Система анализа логов посещений
