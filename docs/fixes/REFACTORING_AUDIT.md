# Аудит проекта LogStorm для рефакторинга

Дата: 19 декабря 2025 г.

## 📁 Структура проекта

### ✅ Основные исполняемые файлы (ОСТАВИТЬ)
- `main.py` - CLI интерфейс
- `gui_app.py` - GUI приложение
- `run_gui.py` - Launcher для GUI
- `manage_mapping.py` - Утилита управления маппингом
- `config.py` - Основная конфигурация
- `gui_config.py` - GUI конфигурация

### ❌ Устаревшие исполняемые файлы (УДАЛИТЬ)
- `main_old.py` - Старая версия CLI
- `main_test.py` - Тестовая версия (дубль)
- `encode_credentials.py` - Не используется
- `update_mapping_from_prefs.py` - Устарело (заменено manage_mapping.py)
- `examples_person_mapper.py` - Демо скрипт (перенести в tests/)

### 🧪 Тестовые файлы (РЕОРГАНИЗОВАТЬ)
#### Актуальные тесты (переместить в tests/)
- `test_mapping_optional.py` - ✅ Тест aliases с/без маппинга
- `test_melanya_mapping.py` - ✅ Тест конкретного кейса
- `test_ndjson_with_mapper.py` - ✅ Тест NDJSON + PersonMapper

#### Устаревшие/Дублирующие тесты (УДАЛИТЬ)
- `test_gui_ndjson.py` - Дубль функционала
- `test_event_merging.py` - Устарело
- `test_models.py` - Минимальная ценность
- `test_multiple_files.py` - Покрыто другими тестами
- `test_ndjson_loader.py` - Дубль
- `test_without_prefs.py` - Устарело

### 📚 Документация (КОНСОЛИДИРОВАТЬ)
#### Основная документация (оставить и обновить)
- `README.md` - Главный файл (обновить)
- `CHANGELOG.md` - История изменений (актуализировать)
- `SECURITY.md` - Безопасность (оставить)

#### Устаревшая/Дублирующая документация (УДАЛИТЬ после переноса в README)
- `CHANGELOG_GUI.md` - Объединить в CHANGELOG.md
- `CHANGELOG_v2.7.md` - Объединить в CHANGELOG.md
- `CHANGELOG_v2.8.md` - Объединить в CHANGELOG.md
- `CLASSIFICATION_GUIDE.md` - Перенести в README
- `GIGACHAT_SETUP.md` - Перенести в README раздел AI
- `GUI_GUIDE.md` - Перенести в README
- `GUI_NDJSON_CHECKLIST.md` - Устарело
- `GUI_NDJSON_FIX.md` - Устарело
- `GUI_NDJSON_GUIDE.md` - Перенести в README
- `IMPLEMENTATION_SUMMARY.md` - Устарело
- `MULTIPLE_FILES_GUIDE.md` - Перенести в README
- `NDJSON_MAPPING_GUIDE.md` - Перенести в README
- `OPTIONAL_PREFS_GUIDE.md` - Устарело
- `QUICKSTART_NDJSON.md` - Перенести в README
- `REFACTORING.md` - Устарело
- `REFACTORING_PLAN.md` - Устарело
- `TESTING_PERSON_MAPPER.md` - Перенести в tests/README.md
- `ai_summary.txt` - Удалить (старая версия)

### 🗂️ Директории с кодом (ОСТАВИТЬ, проверить содержимое)
- `analyzers/` - ✅ Анализаторы посещаемости
- `models/` - ✅ Модели данных
- `reporters/` - ✅ Генерация отчетов
- `services/` - ✅ Бизнес-логика
- `utils/` - ✅ Утилиты
- `validators/` - ✅ Валидаторы

### 📊 Директории с данными
- `logs/` - ✅ Логи (оставить)
- `LogsCam/` - ✅ NDJSON данные (оставить)
- `reports/` - ✅ Выходные отчеты (оставить)
- `path/` - ⚠️ Проверить содержимое
- `Server-Log-2025-12-15 17-57-32/` - ⚠️ Временные данные (добавить в .gitignore)

### 🔧 Файлы конфигурации (ОСТАВИТЬ)
- `.env` - Переменные окружения
- `.env.example` - Пример конфигурации
- `.gitignore` - Git исключения
- `requirements.txt` - Зависимости
- `setup.py` - Установка пакета

### 📦 Данные конфигурации (УПРОСТИТЬ)
- `person_mapping.json` - ✅ ОСНОВНОЙ файл маппинга (ОСТАВИТЬ)
- `person_prefs.json` - ❌ ДУБЛЬ (УДАЛИТЬ, заменен person_mapping.json)

## 🎯 План действий

### Фаза 1: Очистка (Priority: HIGH)
1. ✅ Удалить устаревшие .py файлы
2. ✅ Удалить дублирующие тесты
3. ✅ Удалить person_prefs.json
4. ✅ Переместить актуальные тесты в tests/

### Фаза 2: Реорганизация документации (Priority: HIGH)
1. ✅ Создать новый README с разделами
2. ✅ Объединить CHANGELOG файлы
3. ✅ Удалить устаревшие .md файлы

### Фаза 3: Оптимизация кода (Priority: MEDIUM)
1. ✅ Проверить дубли в config.py и gui_config.py
2. ✅ Проверить неиспользуемые импорты
3. ✅ Обновить docstrings

### Фаза 4: Финализация (Priority: LOW)
1. ✅ Обновить .gitignore
2. ✅ Создать tests/README.md
3. ✅ Проверить все импорты после перемещений

## 📊 Статистика

### До рефакторинга:
- Файлов .py: ~20
- Файлов .md: ~20
- Тестов: 9
- Конфигурационных файлов: 2 (дубль!)

### После рефакторинга (целевое):
- Файлов .py: ~8 (основных)
- Файлов .md: ~4 (README, CHANGELOG, SECURITY, tests/README)
- Тестов: 3-4 (актуальных в tests/)
- Конфигурационных файлов: 1 (person_mapping.json)
