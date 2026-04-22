# 🚀 Quick Start: Рефакторинг LogStorm

> Historical note: GUI refactoring is no longer active. The GUI layer was
> removed from current LogStorm scope; use `main.py`, API and collector.

**Полный план**: `REFACTORING_MASTER_PLAN.md`

---

## 📊 Текущие проблемы

1. **gui_app_fluent.py** - 1991 строка (монолит)
2. **Нет тестов** - покрытие ~5%
3. **Смешанная конфигурация** - config.py, config.json, хардкод
4. **Слабое логирование** - print() вместо logger
5. **Нет DI** - жесткие связи модулей

---

## 🎯 8 Фаз рефакторинга

### ⚡ Фаза 1: Декомпозиция GUI (2 недели) [ВЫСОКИЙ]
**Цель**: Разбить gui_app_fluent.py (1991 строка) на модули

**До**:
```
gui_app_fluent.py (1991 строка)
```

**После**:
```
gui/
├── main_window.py (300 строк)
├── state/app_state.py (150 строк)
├── interfaces/ (6 файлов × 200 строк)
├── dialogs/ (1 файл × 100 строк)
└── workers/ (2 файла × 150 строк)
```

**Действия**:
1. Создать папку `gui/`
2. Вынести workers → `gui/workers/`
3. Вынести dialogs → `gui/dialogs/`
4. Вынести state → `gui/state/`
5. Вынести interfaces → `gui/interfaces/`
6. Создать `main_window.py`
7. Обновить `run_gui.py`

---

### ⚙️ Фаза 2: Унификация конфигурации (1 неделя) [ВЫСОКИЙ]
**Цель**: Централизовать настройки

**Актуальная цель после architecture cleanup**:
```python
core/settings.py      # единый settings module
```

**Было**:
`LATE_THRESHOLD_MINUTES` импортировался из удаленного legacy-пакета `config`.

**Станет**:
```python
from core.settings import LATE_THRESHOLD_MINUTES
```

---

### 📝 Фаза 3: Логирование (1 неделя) [СРЕДНИЙ]
**Цель**: Убрать print(), добавить logger

**Создать**:
```python
# utils/logging.py
logger = setup_logging()

# exceptions.py
class LogStormError(Exception): pass
class ConfigError(LogStormError): pass
```

**Было**:
```python
print("Загрузка файла...")
```

**Станет**:
```python
logger.info("Загрузка файла", extra={'path': file_path})
```

---

### 🔌 Фаза 4: Dependency Injection (1 неделя) [СРЕДНИЙ]
**Цель**: Убрать жесткие связи

```python
# di_container.py
class Container(containers.DeclarativeContainer):
    config = providers.Configuration()
    data_loader = providers.Singleton(DataLoader)
    attendance_service = providers.Factory(
        AttendanceService,
        data_loader=data_loader
    )
```

---

### 🧪 Фаза 5: Тестирование (1 неделя) [ВЫСОКИЙ]
**Цель**: Покрытие >70%

```
tests/
├── unit/
│   ├── test_analyzers.py
│   ├── test_services.py
│   └── test_validators.py
└── integration/
    └── test_data_flow.py
```

**Цели покрытия**:
- Analyzers: 90%+
- Models: 95%+
- Services: 80%+
- GUI: 50%+

---

### 📘 Фаза 6: Типизация (2 недели) [НИЗКИЙ]
**Цель**: mypy strict mode

```python
def analyze_late(record: AttendanceRecord) -> Tuple[bool, int]:
    """Полная типизация всех параметров и возвратов"""
```

---

### 📚 Фаза 7: Документация (1 неделя) [СРЕДНИЙ]
**Цель**: API docs

```python
def analyze_late(record: AttendanceRecord) -> Tuple[bool, int]:
    """
    Анализирует опоздание сотрудника.
    
    Args:
        record: Запись посещения
        
    Returns:
        Кортеж (is_late, late_minutes)
    """
```

---

### ⚡ Фаза 8: Оптимизация (2 недели) [НИЗКИЙ]
**Цель**: Performance tuning

- Профилирование (cProfile)
- Оптимизация pandas
- Кеширование (@lru_cache)

---

## 🎯 Метрики успеха

```
✅ Нет файлов >500 строк
✅ Покрытие тестами >70%
✅ mypy без ошибок
✅ pylint score >9.0
✅ Анализ 1000 записей <1 сек
```

---

## 🔧 Начать сейчас

### 1. Создать ветку
```bash
git checkout -b refactoring/phase1-gui-decomposition
```

### 2. Создать структуру
```bash
mkdir -p gui/{state,interfaces,dialogs,workers}
touch gui/__init__.py
touch gui/state/__init__.py
touch gui/interfaces/__init__.py
touch gui/dialogs/__init__.py
touch gui/workers/__init__.py
```

### 3. Начать с workers
```bash
# Вынести AnalysisWorker из gui_app_fluent.py
# в gui/workers/analysis_worker.py
```

### 4. Тестировать
```bash
python run_gui.py
# Проверить что всё работает
```

---

## 📅 Расписание

| Фаза | Приоритет | Время | Старт |
|------|-----------|-------|-------|
| 1. GUI декомпозиция | 🔴 ВЫСОКИЙ | 2 нед | Сейчас |
| 2. Конфигурация | 🔴 ВЫСОКИЙ | 1 нед | Неделя 3 |
| 3. Логирование | 🟡 СРЕДНИЙ | 1 нед | Неделя 4 |
| 4. DI | 🟡 СРЕДНИЙ | 1 нед | Неделя 5 |
| 5. Тесты | 🔴 ВЫСОКИЙ | 1 нед | Неделя 6 |
| 6. Типизация | 🟢 НИЗКИЙ | 2 нед | Неделя 7-8 |
| 7. Документация | 🟡 СРЕДНИЙ | 1 нед | Неделя 9 |
| 8. Оптимизация | 🟢 НИЗКИЙ | 2 нед | Неделя 10-11 |

**Итого**: ~11 недель (3 месяца)

---

## 📝 Чек-лист перед началом

- [x] План утвержден
- [ ] Backup создан
- [ ] Все изменения закоммичены
- [ ] Feature branch создана
- [ ] Зависимости установлены

---

## 🚀 Следующий шаг

**Начать Фазу 1**: Декомпозиция GUI

```bash
# 1. Создать ветку
git checkout -b refactoring/phase1-gui-decomposition

# 2. Создать структуру папок
mkdir -p gui/{state,interfaces,dialogs,workers}

# 3. Начать с workers
# Открыть gui_app_fluent.py
# Скопировать AnalysisWorker → gui/workers/analysis_worker.py
```

---

**Детали**: `REFACTORING_MASTER_PLAN.md`  
**Статус**: Готов к старту ✅
