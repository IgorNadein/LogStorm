"""
Конфигурационный файл с константами для LogStorm
"""

# === ПУТИ К ФАЙЛАМ ===
LOGS_FILE = 'logs/attendance.csv'
PERSON_MAPPING_FILE = 'person_mapping.json'  # Основной файл маппинга
OUTPUT_EXCEL_FILE = 'attendance_report.xlsx'
OUTPUT_AI_SUMMARY_FILE = 'ai_summary.txt'

# === РАБОЧИЙ ГРАФИК ===
DEFAULT_WORK_HOURS = 9  # Стандартная продолжительность рабочего дня (часов)
DEFAULT_START_TIME = '08:00'  # Стандартное время начала работы
DEFAULT_END_TIME = '17:00'  # Стандартное время окончания работы

# Дефолтное расписание для маппинга сотрудников
DEFAULT_SCHEDULE = {
    'workdays': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
    'start_time': '09:00',
    'end_time': '18:00',
    'work_hours': 9
}

# === ПОРОГИ ДЛЯ АНАЛИЗА ===
OVERTIME_THRESHOLD = 10  # Переработка: более N часов в день
LATE_THRESHOLD_MINUTES = 15  # Опоздание учитывается если больше N минут
CRITICAL_LATE_MINUTES = 180  # Критическое опоздание (3+ часа) = сбой системы
CRITICAL_UNDERWORK_HOURS = 7  # Критическая недоработка: менее N часов
CRITICAL_UNDERWORK_DIFF = 2  # Критическая недоработка: на N+ часов меньше нормы
MASS_ABSENCE_THRESHOLD = 0.8  # Массовое отсутствие: если отсутствует >80% работников
CRITICAL_ABSENCE_THRESHOLD = 1.0  # Критическое отсутствие: 100% отсутствуют (включая выходные)

# === ВРЕМЕННЫЕ ДИАПАЗОНЫ ===
NIGHT_HOUR_START = 23  # Начало ночного времени (час)
NIGHT_HOUR_END = 3  # Конец ночного времени (час)

# === EXCEL ФОРМАТИРОВАНИЕ ===
# Цвета заголовков
HEADER_COLOR = "4472C4"  # Синий
SUMMARY_HEADER_COLOR = "9966CC"  # Фиолетовый (для итоговых столбцов)

# Цвета фона строк (светлые)
LATE_BG_COLOR = "FFE699"  # Светло-желтый (опоздания)
OVERTIME_BG_COLOR = "C6EFCE"  # Светло-зеленый (переработки)
SUSPICIOUS_BG_COLOR = "FFB3B3"  # Светло-красный (технические сбои)

# Цвета ячеек (яркие)
LATE_CELL_COLOR = "FFA500"  # Оранжевый (конкретное опоздание)
UNDERWORK_CELL_COLOR = "FFFF00"  # Желтый (недоработка)
OVERTIME_CELL_COLOR = "00B050"  # Зеленый (переработка)
SUSPICIOUS_CELL_COLOR = "8B0000"  # Темно-красный (технический сбой)
TECHNICAL_FILL_COLOR = "FF0000"  # Красный (технический сбой в месячных отчетах)

# === НАЗВАНИЯ ЛИСТОВ EXCEL ===
SHEET_MAIN_REPORT = 'Отчет по дням'
SHEET_SUSPICIOUS = 'Подозрительные случаи'
SHEET_MONTH_PREFIX = 'Месяц '

# === СТАТИСТИКА ===
TOP_N_USERS = 5  # Количество пользователей в топах (опоздания, переработки)
MAX_SUSPICIOUS_DETAILS = 10  # Максимум деталей подозрительных случаев в консоли

# === AI АНАЛИЗ ===
GIGACHAT_SCOPE = 'GIGACHAT_API_PERS'  # Scope для GigaChat API
AI_PROMPT_SENTENCES = 5  # Количество предложений в AI сводке

# === НАЗВАНИЯ ДЛЯ ОТЧЕТОВ ===
DAYS_RU = {
    'Monday': 'Понедельник',
    'Tuesday': 'Вторник',
    'Wednesday': 'Среда',
    'Thursday': 'Четверг',
    'Friday': 'Пятница',
    'Saturday': 'Суббота',
    'Sunday': 'Воскресенье'
}

DAYS_ORDER = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

# === МЕСЯЦЫ ===
MONTHS_RU = {
    1: 'Январь',
    2: 'Февраль',
    3: 'Март',
    4: 'Апрель',
    5: 'Май',
    6: 'Июнь',
    7: 'Июль',
    8: 'Август',
    9: 'Сентябрь',
    10: 'Октябрь',
    11: 'Ноябрь',
    12: 'Декабрь'
}
