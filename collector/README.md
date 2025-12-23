# LogStorm Collector

Фоновый сборщик событий СКУД для Windows Server.

## 🎯 Назначение

Запускается на Windows Server в фоновом режиме и собирает события 
с нескольких устройств Hikvision/HiWatch по расписанию в один NDJSON файл.

## 🚀 Быстрый старт

### 1. Настройка

```bash
# Создать пример конфигурации
python collector.py --init

# Отредактировать collector.json
```

### 2. Тестовый запуск

```bash
# Однократный сбор
python collector.py --once --verbose

# Запуск в консоли (для тестирования)
python collector.py --verbose
```

### 3. Установка как Windows служба

```bash
# Установить
python collector.py install

# Запустить
python collector.py start

# Остановить
python collector.py stop

# Удалить
python collector.py remove
```

## ⚙️ Конфигурация (collector.json)

```json
{
  "output_file": "//SERVER/share/logstorm/events.ndjson",
  "log_file": "collector.log",
  "interval_minutes": 15,
  "devices": [
    {
      "name": "Камера входа",
      "host": "192.168.1.101",
      "user": "admin",
      "password": "YOUR_PASSWORD",
      "enabled": true
    },
    {
      "name": "Камера выхода",
      "host": "192.168.1.102",
      "user": "admin", 
      "password": "YOUR_PASSWORD",
      "enabled": true
    }
  ],
  "request": {
    "page_size": 30,
    "timeout": 180,
    "retries": 3,
    "major": 5,
    "minor": 0
  }
}
```

### Параметры

| Параметр | Описание |
|----------|----------|
| `output_file` | Путь к выходному файлу (UNC для сетевой папки) |
| `log_file` | Файл логов |
| `interval_minutes` | Интервал сбора в минутах |
| `devices` | Массив устройств |
| `devices[].name` | Понятное имя устройства |
| `devices[].host` | IP-адрес |
| `devices[].user` | Логин |
| `devices[].password` | Пароль |
| `devices[].enabled` | Активно ли устройство |

## 📁 Структура файлов

```
collector/
├── collector.py           # Основной скрипт
├── collector.json         # Конфигурация (создать вручную)
├── collector.example.json # Пример конфигурации
├── collector.log          # Лог работы (создаётся автоматически)
├── collector_state.json   # Состояние (создаётся автоматически)
└── README.md
```

## 🔄 Как это работает

1. **Запуск** — сборщик читает конфигурацию
2. **Для каждого устройства:**
   - Определяет время последнего сбора (или 30 дней назад для первого запуска)
   - Запрашивает события от этого времени до текущего
   - Фильтрует дубликаты по `serialNo`
   - Дописывает новые события в общий файл
3. **Ожидание** — ждёт N минут до следующего сбора
4. **Повтор**

## 📊 Формат вывода

Каждое событие дополняется метаданными:

```json
{
  "major": 5,
  "minor": 75,
  "time": "2025-12-22T08:30:00+03:00",
  "serialNo": 12345,
  "name": "Employee Sample Employee Sample",
  "_device": "192.168.1.101",
  "_device_name": "Камера входа",
  "_collected": "2025-12-22T10:15:00"
}
```

## 🛡️ Дедупликация

- Хранит `serialNo` последних 10000 событий для каждого устройства
- Состояние сохраняется в `collector_state.json`
- При перезапуске загружает состояние и продолжает без дубликатов

## 📋 Требования

```
pip install requests requests-toolbelt pywin32
```

`pywin32` нужен только для установки как Windows службы.

## 🔧 Команды

| Команда | Описание |
|---------|----------|
| `python collector.py --init` | Создать пример конфига |
| `python collector.py --once` | Однократный сбор |
| `python collector.py` | Запуск в цикле |
| `python collector.py -v` | С подробным выводом |
| `python collector.py install` | Установить службу |
| `python collector.py start` | Запустить службу |
| `python collector.py stop` | Остановить службу |
| `python collector.py remove` | Удалить службу |
