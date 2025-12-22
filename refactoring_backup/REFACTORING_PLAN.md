# План детального рефакторинга LogStorm

## 🎯 Цель
Разделить монолитный `main.py` (1131 строка) на логические модули с чёткой ответственностью.

---

## 📊 Текущее состояние

### Проблемы:
1. **Всё в одном файле** - 1131 строка в `main.py`
2. **Смешанная логика** - валидация, определение статусов, форматирование в одном методе
3. **Дублирование** - подсчёт итогов использует те же условия, что и основной анализ
4. **Сложная читаемость** - метод `analyze_attendance()` содержит ~200 строк с вложенными условиями
5. **Нет переиспользования** - логика определения "технического сбоя" размазана по коду

---

## 🏗️ Новая архитектура

```
LogStorm/
├── config.py                    # ✅ Уже есть - константы
├── main.py                      # 🔄 Упростить - точка входа
│
├── models/                      # 📦 НОВЫЙ - модели данных
│   ├── __init__.py
│   ├── attendance_record.py     # Класс AttendanceRecord (одна запись)
│   └── work_schedule.py         # Класс WorkSchedule (график работы)
│
├── validators/                  # ✅ НОВЫЙ - валидация данных
│   ├── __init__.py
│   ├── time_validator.py        # Валидация времени (ночное время, аномалии)
│   └── absence_validator.py     # Массовые/критические отсутствия
│
├── analyzers/                   # ✅ НОВЫЙ - определение статусов
│   ├── __init__.py
│   ├── status_analyzer.py       # Опоздания, недоработки, переработки
│   └── technical_analyzer.py    # Технические сбои системы
│
├── reporters/                   # 📊 НОВЫЙ - генерация отчётов
│   ├── __init__.py
│   ├── excel_reporter.py        # Генерация Excel
│   ├── excel_formatter.py       # Форматирование Excel
│   └── summary_reporter.py      # Текстовые сводки
│
├── services/                    # 🔧 НОВЫЙ - бизнес-логика
│   ├── __init__.py
│   ├── data_loader.py           # Загрузка CSV/JSON
│   ├── attendance_service.py    # Основной сервис анализа
│   └── ai_service.py            # GigaChat интеграция
│
└── utils/                       # 🛠️ НОВЫЙ - утилиты
    ├── __init__.py
    ├── date_utils.py            # Работа с датами
    └── excel_utils.py           # Утилиты Excel (стили, границы)
```

---

## 📋 Детальный план по модулям

### 1️⃣ **models/** - Модели данных

#### `models/attendance_record.py`
```python
@dataclass
class AttendanceRecord:
    """Одна запись посещаемости за день"""
    date: date
    user_name: str
    display_name: str
    arrival_time: Optional[time]
    departure_time: Optional[time]
    work_hours: float
    appearances: int
    
    # Контекст
    weekday: str
    is_workday: bool
    schedule_start: time
    schedule_end: time
    expected_hours: float
    
    # Статусы (заполняются анализаторами)
    is_late: bool = False
    late_minutes: int = 0
    is_early_leave: bool = False
    early_leave_minutes: int = 0
    is_underwork: bool = False
    is_overtime: bool = False
    
    # Проблемы
    technical_issues: List[str] = field(default_factory=list)
    employee_issues: List[str] = field(default_factory=list)
    
    @property
    def has_technical_issues(self) -> bool:
        return len(self.technical_issues) > 0
    
    @property
    def is_valid_record(self) -> bool:
        """Валидная запись = нет технических сбоев"""
        return not self.has_technical_issues
```

#### `models/work_schedule.py`
```python
@dataclass
class WorkSchedule:
    """График работы пользователя"""
    start_time: time
    end_time: time
    workdays: List[str]  # ['Monday', 'Tuesday', ...]
    expected_hours: float
    
    def is_workday(self, weekday: str) -> bool:
        return weekday in self.workdays
```

---

### 2️⃣ **validators/** - Валидация данных

#### `validators/time_validator.py`
```python
class TimeValidator:
    """Валидация временных данных"""
    
    @staticmethod
    def filter_night_entries(entries: pd.DataFrame) -> pd.DataFrame:
        """Фильтрует ночные записи (23:00-04:00)"""
        return entries[
            (entries['timestamp'].dt.hour >= NIGHT_HOUR_END) &
            (entries['timestamp'].dt.hour < NIGHT_HOUR_START)
        ]
    
    @staticmethod
    def has_night_activity(entries: pd.DataFrame) -> bool:
        """Проверяет наличие ночной активности"""
        night_entries = entries[
            (entries['timestamp'].dt.hour < NIGHT_HOUR_END) |
            (entries['timestamp'].dt.hour >= NIGHT_HOUR_START)
        ]
        return len(night_entries) > 0
    
    @staticmethod
    def is_extreme_late(late_minutes: int) -> bool:
        """Экстремальное опоздание (>3 часа)"""
        return late_minutes >= CRITICAL_LATE_MINUTES
    
    @staticmethod
    def is_critical_underwork(work_hours: float, expected_hours: float) -> bool:
        """Критическая недоработка (<7ч или на 2+ч меньше нормы)"""
        hours_diff = expected_hours - work_hours
        return (work_hours < CRITICAL_UNDERWORK_HOURS or 
                hours_diff >= CRITICAL_UNDERWORK_DIFF)
```

#### `validators/absence_validator.py`
```python
class AbsenceValidator:
    """Валидация массовых отсутствий"""
    
    def __init__(self, df: pd.DataFrame, prefs: dict):
        self.df = df
        self.prefs = prefs
    
    def detect_mass_absence_days(self) -> Set[date]:
        """Дни с >90% отсутствующих на рабочих местах"""
        # ... текущая логика из _detect_mass_absence_days
    
    def detect_critical_absence_days(self) -> Set[date]:
        """Дни со 100% отсутствием (включая выходные)"""
        # ... текущая логика из _detect_critical_absence_days
```

---

### 3️⃣ **analyzers/** - Определение статусов

#### `analyzers/technical_analyzer.py`
```python
class TechnicalIssueAnalyzer:
    """Определение технических сбоев системы"""
    
    def __init__(self, 
                 mass_absence_dates: Set[date],
                 critical_absence_dates: Set[date]):
        self.mass_absence_dates = mass_absence_dates
        self.critical_absence_dates = critical_absence_dates
    
    def analyze(self, record: AttendanceRecord, 
                entries: Optional[pd.DataFrame]) -> List[str]:
        """Возвращает список технических проблем"""
        issues = []
        
        # 1. Критическое отсутствие (100%)
        if record.date in self.critical_absence_dates:
            issues.append("День критического отсутствия (100% отсутствуют)")
            return issues  # Остальное не проверяем
        
        # 2. Массовое отсутствие (>90%)
        if (record.date in self.mass_absence_dates and 
            record.is_workday):
            issues.append("День массового отсутствия (>90% отсутствуют)")
            return issues
        
        # Если нет записей - не технический сбой
        if entries is None or record.appearances == 0:
            return issues
        
        # 3. Ночная активность (только в рабочие дни)
        if record.is_workday and TimeValidator.has_night_activity(entries):
            issues.append("Ночная активность")
        
        # 4. Одно появление
        if record.appearances == 1:
            issues.append("Одно появление")
        
        # 5. Экстремальное опоздание
        if (record.is_late and 
            TimeValidator.is_extreme_late(record.late_minutes)):
            issues.append(
                f"Экстремальное опоздание "
                f"({record.late_minutes//60}ч {record.late_minutes%60}м)"
            )
        
        # 6. Критическая недоработка
        if TimeValidator.is_critical_underwork(
            record.work_hours, record.expected_hours):
            issues.append(
                f"Критическая недоработка ({record.work_hours:.1f}ч)"
            )
        
        return issues
```

#### `analyzers/status_analyzer.py`
```python
class StatusAnalyzer:
    """Определение статусов сотрудника (опоздания, переработки и т.д.)"""
    
    @staticmethod
    def analyze_late(record: AttendanceRecord) -> Tuple[bool, int]:
        """Проверка опоздания"""
        if not record.is_workday or not record.arrival_time:
            return False, 0
        
        if record.arrival_time > record.schedule_start:
            late_delta = (
                datetime.combine(record.date, record.arrival_time) -
                datetime.combine(record.date, record.schedule_start)
            )
            late_minutes = int(late_delta.total_seconds() / 60)
            
            # Опоздание учитывается только >15 минут
            if late_minutes > LATE_THRESHOLD_MINUTES:
                return True, late_minutes
        
        return False, 0
    
    @staticmethod
    def analyze_early_leave(record: AttendanceRecord) -> Tuple[bool, int]:
        """Проверка раннего ухода"""
        if not record.is_workday or not record.departure_time:
            return False, 0
        
        if record.departure_time < record.schedule_end:
            underwork_delta = (
                datetime.combine(record.date, record.schedule_end) -
                datetime.combine(record.date, record.departure_time)
            )
            underwork_minutes = int(underwork_delta.total_seconds() / 60)
            return True, underwork_minutes
        
        return False, 0
    
    @staticmethod
    def analyze_underwork(record: AttendanceRecord) -> bool:
        """Проверка недоработки по часам"""
        if not record.is_workday:
            return False
        return record.work_hours < record.expected_hours
    
    @staticmethod
    def analyze_overtime(record: AttendanceRecord) -> bool:
        """Проверка переработки"""
        if record.is_workday:
            # В рабочий день - если >10 часов
            return record.work_hours > OVERTIME_THRESHOLD
        else:
            # В выходной - любая работа = переработка
            return record.appearances > 0
    
    @staticmethod
    def get_employee_issues(record: AttendanceRecord) -> List[str]:
        """Проблемы сотрудника (только если НЕТ технических сбоев)"""
        if record.has_technical_issues:
            return []
        
        issues = []
        
        # Отсутствие в рабочий день
        if (record.appearances == 0 and record.is_workday):
            issues.append("Отсутствие")
            return issues
        
        # Опоздание (15 мин - 3 часа)
        if (record.is_late and 
            LATE_THRESHOLD_MINUTES < record.late_minutes < CRITICAL_LATE_MINUTES):
            issues.append(f"Опоздание {record.late_minutes} мин")
        
        # Недоработка (не критическая)
        hours_diff = record.expected_hours - record.work_hours
        if (record.is_underwork and 
            hours_diff < CRITICAL_UNDERWORK_DIFF and
            record.work_hours >= CRITICAL_UNDERWORK_HOURS):
            issues.append(f"Недоработка {hours_diff:.1f}ч")
        
        return issues
```

---

### 4️⃣ **services/** - Бизнес-логика

#### `services/data_loader.py`
```python
class DataLoader:
    """Загрузка данных из файлов"""
    
    @staticmethod
    def load_logs(path: str) -> pd.DataFrame:
        """Загрузка логов из CSV"""
        df = pd.read_csv(path)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['date'] = df['timestamp'].dt.date
        df['time'] = df['timestamp'].dt.time
        return df
    
    @staticmethod
    def load_preferences(path: str) -> dict:
        """Загрузка настроек пользователей из JSON"""
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @staticmethod
    def filter_known_users(df: pd.DataFrame, prefs: dict) -> pd.DataFrame:
        """Фильтрация только пользователей с профилями"""
        known_users = set(prefs.keys())
        return df[df['name'].isin(known_users)]
```

#### `services/attendance_service.py`
```python
class AttendanceService:
    """Основной сервис анализа посещаемости"""
    
    def __init__(self, df: pd.DataFrame, prefs: dict):
        self.df = df
        self.prefs = prefs
        
        # Инициализация валидаторов
        absence_validator = AbsenceValidator(df, prefs)
        self.mass_absence_dates = absence_validator.detect_mass_absence_days()
        self.critical_absence_dates = absence_validator.detect_critical_absence_days()
        
        # Инициализация анализаторов
        self.technical_analyzer = TechnicalIssueAnalyzer(
            self.mass_absence_dates,
            self.critical_absence_dates
        )
    
    def analyze_all(self) -> List[AttendanceRecord]:
        """Анализ всех пользователей за все дни"""
        records = []
        
        min_date = self.df['date'].min()
        max_date = self.df['date'].max()
        all_dates = pd.date_range(start=min_date, end=max_date, freq='D').date
        all_users = list(self.prefs.keys())
        
        grouped = self.df.groupby(['name', 'date'])
        
        for user_name in all_users:
            for date in all_dates:
                record = self._analyze_user_day(
                    user_name, date, grouped
                )
                records.append(record)
        
        return records
    
    def _analyze_user_day(self, 
                         user_name: str, 
                         date: date, 
                         grouped) -> AttendanceRecord:
        """Анализ одного пользователя за один день"""
        
        # 1. Создание базовой записи
        record = self._create_base_record(user_name, date, grouped)
        
        # 2. Определение базовых статусов (опоздание, ранний уход и т.д.)
        record.is_late, record.late_minutes = StatusAnalyzer.analyze_late(record)
        record.is_early_leave, record.early_leave_minutes = StatusAnalyzer.analyze_early_leave(record)
        record.is_underwork = StatusAnalyzer.analyze_underwork(record)
        record.is_overtime = StatusAnalyzer.analyze_overtime(record)
        
        # 3. Определение технических сбоев
        entries = grouped.get_group((user_name, date)) if (user_name, date) in grouped.groups else None
        record.technical_issues = self.technical_analyzer.analyze(record, entries)
        
        # 4. Определение проблем сотрудника (только если нет технических сбоев)
        record.employee_issues = StatusAnalyzer.get_employee_issues(record)
        
        return record
    
    def _create_base_record(self, 
                           user_name: str, 
                           date: date, 
                           grouped) -> AttendanceRecord:
        """Создание базовой записи с временными данными"""
        # ... извлечение времени прихода/ухода, фильтрация ночных записей
        # ... возвращает AttendanceRecord с заполненными базовыми полями
```

---

### 5️⃣ **reporters/** - Генерация отчётов

#### `reporters/excel_reporter.py`
```python
class ExcelReporter:
    """Генерация Excel отчётов"""
    
    def __init__(self, records: List[AttendanceRecord]):
        self.records = records
    
    def generate_report(self, output_file: str):
        """Генерация полного отчёта"""
        # Конвертация в DataFrame
        df = self._records_to_dataframe()
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # Основной отчёт
            df.to_excel(writer, sheet_name=SHEET_MAIN_REPORT, index=False)
            
            # Подозрительные случаи
            df_suspicious = df[df['Технический сбой'] != 'Нет']
            if not df_suspicious.empty:
                df_suspicious.to_excel(writer, sheet_name=SHEET_SUSPICIOUS, index=False)
            
            # Месячные таблицы
            self._generate_monthly_sheets(writer, df)
        
        # Форматирование
        formatter = ExcelFormatter(output_file, self.records)
        formatter.format_all()
    
    def _records_to_dataframe(self) -> pd.DataFrame:
        """Конвертация AttendanceRecord в DataFrame"""
        # ... преобразование списка records в DataFrame
```

#### `reporters/summary_reporter.py`
```python
class SummaryReporter:
    """Генерация текстовых сводок"""
    
    def __init__(self, records: List[AttendanceRecord]):
        self.records = records
        self.valid_records = [r for r in records if r.is_valid_record]
    
    def print_summary(self):
        """Вывод сводки в консоль"""
        self._print_general_stats()
        self._print_late_stats()
        self._print_overtime_stats()
        self._print_technical_issues()
    
    def _print_general_stats(self):
        """Общая статистика"""
        # ... текущая логика из generate_summary()
```

---

### 6️⃣ **utils/** - Утилиты

#### `utils/date_utils.py`
```python
class DateUtils:
    """Утилиты для работы с датами"""
    
    @staticmethod
    def get_weekday_ru(date: date) -> str:
        """Русское название дня недели"""
        weekday_en = pd.Timestamp(date).day_name()
        return DAYS_RU.get(weekday_en, weekday_en)
    
    @staticmethod
    def get_date_range(start: date, end: date) -> List[date]:
        """Диапазон дат"""
        return pd.date_range(start=start, end=end, freq='D').date
```

#### `utils/excel_utils.py`
```python
class ExcelStyleFactory:
    """Фабрика стилей для Excel"""
    
    @staticmethod
    def create_all_styles() -> dict:
        """Создание всех стилей"""
        # ... текущая логика из _create_styles()
```

---

### 7️⃣ **main.py** - Точка входа (упрощённая)

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LogStorm - Attendance Log Analyzer"""

from services.data_loader import DataLoader
from services.attendance_service import AttendanceService
from services.ai_service import AIService
from reporters.excel_reporter import ExcelReporter
from reporters.summary_reporter import SummaryReporter
from config import LOGS_FILE, PERSON_PREFS_FILE, OUTPUT_EXCEL_FILE


class LogStormApp:
    """Главное приложение"""
    
    def __init__(self):
        self.records = []
    
    def run(self):
        """Запуск анализа"""
        print("="*80)
        print("LogStorm - Анализатор логов посещаемости")
        print("="*80)
        
        # 1. Загрузка данных
        print("\n[1/5] Загрузка данных...")
        df = DataLoader.load_logs(LOGS_FILE)
        prefs = DataLoader.load_preferences(PERSON_PREFS_FILE)
        df = DataLoader.filter_known_users(df, prefs)
        
        # 2. Анализ
        print("[2/5] Анализ посещаемости...")
        service = AttendanceService(df, prefs)
        self.records = service.analyze_all()
        
        # 3. Excel отчёт
        print("[3/5] Генерация Excel отчёта...")
        excel_reporter = ExcelReporter(self.records)
        excel_reporter.generate_report(OUTPUT_EXCEL_FILE)
        
        # 4. Текстовая сводка
        print("[4/5] Генерация сводки...")
        summary_reporter = SummaryReporter(self.records)
        summary_reporter.print_summary()
        
        # 5. AI анализ
        print("[5/5] AI анализ...")
        ai_service = AIService(self.records)
        ai_service.generate_summary()
        
        print("\n[OK] Анализ завершён!")


if __name__ == '__main__':
    app = LogStormApp()
    app.run()
```

---

## 🔄 Порядок выполнения рефакторинга

### Этап 1: Создание структуры (безопасно)
1. ✅ Создать папки: `models/`, `validators/`, `analyzers/`, `services/`, `reporters/`, `utils/`
2. ✅ Создать `__init__.py` во всех папках
3. ✅ Сохранить `main.py` как `main_old.py` (бэкап)

### Этап 2: Модели данных
1. ✅ Создать `models/attendance_record.py`
2. ✅ Создать `models/work_schedule.py`
3. ✅ Тесты: убедиться, что модели создаются корректно

### Этап 3: Валидаторы
1. ✅ Создать `validators/time_validator.py`
2. ✅ Создать `validators/absence_validator.py`
3. ✅ Перенести логику из `_detect_mass_absence_days()` и `_detect_critical_absence_days()`
4. ✅ Тесты: проверить, что валидаторы возвращают те же результаты

### Этап 4: Анализаторы
1. ✅ Создать `analyzers/technical_analyzer.py`
2. ✅ Создать `analyzers/status_analyzer.py`
3. ✅ Перенести логику определения статусов из `analyze_attendance()`
4. ✅ Тесты: сравнить результаты со старой версией

### Этап 5: Сервисы
1. ✅ Создать `services/data_loader.py`
2. ✅ Создать `services/attendance_service.py`
3. ✅ Перенести логику из `analyze_attendance()`
4. ✅ Создать `services/ai_service.py`
5. ✅ Тесты: полный прогон на реальных данных

### Этап 6: Репортеры
1. ✅ Создать `reporters/excel_reporter.py`
2. ✅ Создать `reporters/excel_formatter.py`
3. ✅ Создать `reporters/summary_reporter.py`
4. ✅ Перенести логику генерации отчётов
5. ✅ Тесты: проверить идентичность Excel файлов

### Этап 7: Утилиты
1. ✅ Создать `utils/date_utils.py`
2. ✅ Создать `utils/excel_utils.py`
3. ✅ Перенести вспомогательные функции

### Этап 8: Новый main.py
1. ✅ Создать новый `main.py` (упрощённый)
2. ✅ Интеграция всех модулей
3. ✅ Полное тестирование

### Этап 9: Финализация
1. ✅ Обновить `README.md`
2. ✅ Обновить `requirements.txt` (если нужно)
3. ✅ Удалить `main_old.py` после успешного тестирования

---

## ✨ Преимущества после рефакторинга

### 1. **Читаемость**
- Каждый модуль отвечает за одну задачу
- Легко найти нужный код
- Понятная структура проекта

### 2. **Переиспользование**
```python
# До: логика размазана по 200 строкам
# После:
is_technical = TechnicalIssueAnalyzer.has_issues(record)
```

### 3. **Тестируемость**
```python
# Можно тестировать каждый компонент отдельно
def test_late_detection():
    record = AttendanceRecord(...)
    is_late, minutes = StatusAnalyzer.analyze_late(record)
    assert is_late == True
    assert minutes == 30
```

### 4. **Расширяемость**
- Добавить новый статус? → Добавить метод в `StatusAnalyzer`
- Новый тип отчёта? → Создать класс в `reporters/`
- Новая валидация? → Добавить в `validators/`

### 5. **Исправление бага с итогами**
```python
# analyzers/status_analyzer.py
class StatusAnalyzer:
    @staticmethod
    def should_count_in_summary(record: AttendanceRecord, 
                                status_type: str) -> bool:
        """Учитывать ли запись в итогах"""
        # Опоздания/переработки - только валидные записи
        if status_type in ['late', 'overtime', 'early_leave']:
            return record.is_valid_record
        # Часы - только валидные записи
        if status_type == 'hours':
            return record.is_valid_record
        return True

# Использование:
valid_lates = [r for r in records 
               if r.is_late and StatusAnalyzer.should_count_in_summary(r, 'late')]
```

---

## 📊 Метрики улучшения

| Метрика | До | После |
|---------|-----|--------|
| Размер `main.py` | 1131 строка | ~150 строк |
| Методов в одном классе | 15 | 5 |
| Строк в `analyze_attendance()` | ~200 | ~30 |
| Модулей | 2 (`main.py`, `config.py`) | 15+ |
| Тестируемость | Сложно | Легко |

---

## 🎯 Следующие шаги

Хотите начать рефакторинг? Я могу:

1. **Начать с моделей** - создать `AttendanceRecord` и `WorkSchedule`
2. **Начать с валидаторов** - вынести логику проверок
3. **Начать с анализаторов** - разделить определение статусов
4. **Создать всё сразу** - полный рефакторинг за один раз

Какой вариант предпочитаете? 🚀
