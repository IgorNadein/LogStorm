#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LogStorm Collector - Фоновый сборщик событий СКУД

Запускается как Windows служба или в фоновом режиме.
Собирает события с нескольких устройств по расписанию.

Возможности:
  - Параллельный сбор с нескольких устройств (max_parallel)
  - Защита от потери данных при таймаутах (last_serial tracking)
  - Дедупликация по serialNo (последние 10000 на устройство)
  - Автоматическое возобновление с последней успешной позиции

Использование:
  # Запуск в консоли (для тестирования)
  python collector.py --config collector.json --verbose

  # Установка как Windows служба
  python collector.py install
  python collector.py start

  # Однократный сбор
  python collector.py --once
"""

import argparse
import json
import os
import sys
import logging
import signal
from datetime import datetime, timedelta
from typing import Any, Dict, List, NamedTuple, Optional, Set
from threading import Event, Lock
from concurrent.futures import ThreadPoolExecutor, as_completed

# Попытка импорта для Windows службы
try:
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

import requests
from requests.auth import HTTPDigestAuth
from requests.exceptions import ConnectionError, ReadTimeout

try:
    from requests_toolbelt.multipart.decoder import MultipartDecoder
except ImportError:
    MultipartDecoder = None


# ============================================================================
# КОНФИГУРАЦИЯ
# ============================================================================

DEFAULT_CONFIG = {
    "output_file": "//SERVER/share/logstorm/events.ndjson",
    "log_file": "collector.log",
    "interval_minutes": 15,
    "max_parallel": 4,  # Параллельный сбор с N устройств
    "initial_days": 30,  # Период первого сканирования (дней назад)
    "images": {
        "enabled": False,  # Сохранять изображения лиц
        "folder": "//SERVER/share/logstorm/images",  # Папка для изображений
        "format": "{date}/{employeeNoString}_{serialNo}.jpg"  # Формат имени
    },
    "devices": [
        {
            "name": "Камера входа",
            "host": "192.168.1.101",
            "user": "admin",
            "password": "password",
            "enabled": True
        },
        {
            "name": "Камера выхода",
            "host": "192.168.1.102",
            "user": "admin",
            "password": "password",
            "enabled": True
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


def load_config(config_path: str) -> Dict[str, Any]:
    """Загрузка конфигурации"""
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return DEFAULT_CONFIG.copy()


def save_default_config(config_path: str) -> None:
    """Сохранение конфигурации по умолчанию"""
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)
    print(f"[OK] Создан файл конфигурации: {config_path}")


# ============================================================================
# ЛОГИРОВАНИЕ
# ============================================================================

def setup_logging(log_file: str, verbose: bool = False) -> logging.Logger:
    """Настройка логирования"""
    logger = logging.getLogger("collector")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    
    # Формат
    fmt = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Файл
    fh = logging.FileHandler(log_file, encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    
    # Консоль
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG if verbose else logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    
    return logger


# ============================================================================
# ДЕДУПЛИКАЦИЯ
# ============================================================================

class EventTracker:
    """Отслеживание уже собранных событий"""
    
    def __init__(self, state_file: str = "collector_state.json",
                 initial_days: int = 30):
        self.state_file = state_file
        self.initial_days = initial_days
        self._serials: Dict[str, Set[int]] = {}  # device -> set of serialNo
        self._last_collect: Dict[str, str] = {}   # device -> last datetime
        self._last_serial: Dict[str, int] = {}    # device -> last serialNo
        self._load_state()
    
    def _load_state(self) -> None:
        """Загрузка состояния"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    self._last_collect = data.get('last_collect', {})
                    self._last_serial = data.get('last_serial', {})
                    # serials сохраняем как списки, конвертируем в set
                    for dev, serials in data.get('serials', {}).items():
                        # Храним последние 10000
                        self._serials[dev] = set(serials[-10000:])
            except Exception:
                pass
    
    def _save_state(self) -> None:
        """Сохранение состояния"""
        data = {
            'last_collect': self._last_collect,
            'last_serial': self._last_serial,
            'serials': {k: list(v)[-10000:] for k, v in self._serials.items()}
        }
        with open(self.state_file, 'w') as f:
            json.dump(data, f)
    
    def is_duplicate(self, device: str, serial: int) -> bool:
        """Проверка дубликата"""
        if device not in self._serials:
            self._serials[device] = set()
        
        if serial in self._serials[device]:
            return True
        
        self._serials[device].add(serial)
        return False
    
    def get_last_collect_time(self, device: str) -> Optional[str]:
        """Время последнего сбора для устройства"""
        return self._last_collect.get(device)
    
    def get_last_serial(self, device: str) -> int:
        """Последний успешно собранный serialNo"""
        return self._last_serial.get(device, 1)
    
    def update_last_serial(self, device: str, serial: int) -> None:
        """Обновить последний успешный serialNo"""
        self._last_serial[device] = serial
        self._save_state()
    
    def update_last_collect(self, device: str, timestamp: str) -> None:
        """Обновить время последнего сбора"""
        self._last_collect[device] = timestamp
        self._save_state()
    
    def get_start_time(self, device: str) -> str:
        """Получить время начала для следующего сбора"""
        last = self.get_last_collect_time(device)
        if last:
            # Начинаем за 1 час до последнего сбора (на случай пропусков)
            try:
                dt = datetime.fromisoformat(last.replace('Z', '+00:00'))
                dt = dt - timedelta(hours=1)
                return dt.strftime("%Y-%m-%dT%H:%M:%S")
            except ValueError:
                pass
        
        # Первый запуск - берём период из конфига
        start = datetime.now() - timedelta(days=self.initial_days)
        return start.strftime("%Y-%m-%dT%H:%M:%S")


# ============================================================================
# ISAPI КЛИЕНТ
# ============================================================================


class FetchResult(NamedTuple):
    """Результат сбора с устройства"""
    events: List[Dict[str, Any]]
    last_serial: int
    completed: bool  # True если дошли до конца, False если прервались


def save_image(
    image_data: bytes,
    event: Dict[str, Any],
    images_config: Dict[str, Any],
    logger: logging.Logger
) -> Optional[str]:
    """Сохранение изображения события"""
    folder = images_config.get('folder', 'images')
    fmt = images_config.get('format', '{date}/{employeeNoString}_{serialNo}.jpg')
    
    # Получаем данные для имени файла
    serial = event.get('serialNo', 0)
    employee = event.get('employeeNoString', 'unknown')
    event_time = event.get('time', '')
    
    # Извлекаем дату из времени события
    date_str = event_time[:10] if event_time else 'unknown'
    
    # Формируем имя файла
    filename = fmt.format(
        date=date_str,
        serialNo=serial,
        employeeNoString=employee,
        time=event_time.replace(':', '-') if event_time else 'unknown'
    )
    
    filepath = os.path.join(folder, filename)
    
    # Создаём директорию
    filedir = os.path.dirname(filepath)
    if filedir:
        os.makedirs(filedir, exist_ok=True)
    
    try:
        with open(filepath, 'wb') as f:
            f.write(image_data)
        return filepath
    except Exception as e:
        logger.warning(f"    [WARN] Не удалось сохранить изображение: {e}")
        return None


def fetch_events_from_device(
    device: Dict[str, Any],
    start_time: str,
    end_time: str,
    config: Dict[str, Any],
    logger: logging.Logger,
    start_serial: int = 1
) -> FetchResult:
    """Получение событий с устройства"""
    
    host = device['host']
    user = device['user']
    password = device['password']
    req = config.get('request', {})
    images_cfg = config.get('images', {})
    save_images = images_cfg.get('enabled', False)
    
    base_url = f"http://{host}"
    auth = HTTPDigestAuth(user, password)
    
    session = requests.Session()
    session.headers.update({"Accept": "application/json"})
    
    all_events: List[Dict[str, Any]] = []
    next_serial = start_serial
    last_successful_serial = start_serial
    iteration = 0
    completed = True
    images_saved = 0
    
    logger.debug(f"    Период: {start_time} -> {end_time}")
    logger.debug(f"    Начальный serial: {start_serial}")
    if save_images:
        logger.debug(f"    Сохранение изображений: {images_cfg.get('folder')}")
    
    while True:
        iteration += 1
        cond = {
            "searchID": "collector",
            "searchResultPosition": 0,
            "maxResults": req.get('page_size', 30),
            "major": req.get('major', 5),
            "minor": req.get('minor', 0),
            "startTime": start_time,
            "endTime": end_time,
            "picEnable": save_images,
            "timeReverseOrder": False,
            "beginSerialNo": next_serial,
            "endSerialNo": 3000000000,
        }
        
        url = f"{base_url}/ISAPI/AccessControl/AcsEvent?format=json"
        
        logger.debug(f"    [{iteration}] serial >= {next_serial}...")
        
        try:
            import time as _time
            req_start = _time.perf_counter()
            
            resp = session.post(
                url, auth=auth,
                json={"AcsEventCond": cond},
                timeout=(5, req.get('timeout', 180))
            )
            
            req_elapsed = _time.perf_counter() - req_start
            status = resp.status_code
            logger.debug(f"    [{iteration}] {req_elapsed:.1f}с, HTTP {status}")
            
            if status == 401:
                logger.error("    [ERROR] Авторизация (401)")
                completed = False
                break
            
            if status >= 400:
                logger.error(f"    [ERROR] HTTP {status}")
                completed = False
                break
            
            # Парсинг JSON и изображений
            ct = (resp.headers.get("Content-Type") or "").lower()
            images_data: Dict[str, bytes] = {}  # URL -> image bytes
            
            if "multipart" in ct:
                if MultipartDecoder is None:
                    logger.error("    [ERROR] Нужен requests-toolbelt")
                    completed = False
                    break
                dec = MultipartDecoder(
                    resp.content, resp.headers.get("Content-Type", "")
                )
                payload = None
                for part in dec.parts:
                    pct = part.headers.get(b"Content-Type", b"")
                    if b"application/json" in pct:
                        payload = json.loads(
                            part.content.decode("utf-8", "ignore")
                        )
                    elif b"image/" in pct and save_images:
                        # Извлекаем Content-ID для связи с событием
                        cid = part.headers.get(b"Content-ID", b"")
                        if isinstance(cid, bytes):
                            cid = cid.decode("utf-8", "ignore")
                        # Убираем угловые скобки <...>
                        cid = cid.strip("<>")
                        if cid:
                            images_data[cid] = part.content
                
                if payload is None:
                    logger.error("    [ERROR] Multipart без JSON")
                    completed = False
                    break
            else:
                payload = resp.json()
            
            # Проверка ошибки устройства
            if "statusCode" in payload:
                msg = payload.get('statusString', 'unknown')
                logger.error(f"    [ERROR] Устройство: {msg}")
                completed = False
                break
            
            # Извлечение событий
            acs = payload.get("AcsEvent", {})
            events = acs.get("InfoList", [])
            
            logger.debug(f"    [{iteration}] +{len(events)} событий")
            
            if not events:
                break
            
            # Сохранение изображений (если включено)
            if save_images and images_data:
                for event in events:
                    pic_url = event.get("pictureURL", "")
                    if pic_url and pic_url in images_data:
                        img_path = save_image(
                            images_data[pic_url], event, images_cfg, logger
                        )
                        if img_path:
                            event["_imagePath"] = img_path
                            images_saved += 1
            
            all_events.extend(events)
            
            # Следующий serial
            max_sn = max((e.get("serialNo", 0) for e in events), default=0)
            if max_sn == 0:
                logger.warning(f"    [{iteration}] Нет serialNo")
                break
            
            last_successful_serial = max_sn
            next_serial = max_sn + 1
            
            page_size = req.get('page_size', 30)
            logger.debug(
                f"    [{iteration}] Всего: {len(all_events)}, "
                f"next: {next_serial}"
            )
            
            if len(events) < page_size:
                break
                
        except ReadTimeout:
            timeout = req.get('timeout', 180)
            logger.warning(f"    [WARN] Таймаут (>{timeout}с)")
            completed = False
            break
        except ConnectionError as e:
            logger.warning(f"    [WARN] Соединение: {e}")
            completed = False
            break
        except Exception as e:
            logger.error(f"    [ERROR] {type(e).__name__}: {e}")
            completed = False
            break
    
    session.close()
    
    if save_images and images_saved > 0:
        logger.debug(f"    Сохранено изображений: {images_saved}")
    
    logger.debug(
        f"    Итого: {len(all_events)}, last_serial: {last_successful_serial}"
    )
    return FetchResult(all_events, last_successful_serial, completed)


# ============================================================================
# СБОРЩИК
# ============================================================================

class Collector:
    """Основной класс сборщика"""
    
    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        self.config = config
        self.logger = logger
        initial_days = config.get('initial_days', 30)
        self.tracker = EventTracker(initial_days=initial_days)
        self.stop_event = Event()
        self._file_lock = Lock()  # Для потокобезопасной записи
    
    def _collect_from_device(
        self, device: Dict[str, Any], end_time: str
    ) -> Dict[str, Any]:
        """Сбор с одного устройства (для параллельного запуска)"""
        host = device['host']
        name = device.get('name', host)
        
        result_info = {
            'host': host,
            'name': name,
            'new': 0,
            'dup': 0,
            'completed': False,
            'error': None
        }
        
        try:
            start_time = self.tracker.get_start_time(host)
            start_serial = self.tracker.get_last_serial(host)
            
            self.logger.info(f"  📹 {name} ({host})")
            
            result = fetch_events_from_device(
                device, start_time, end_time, self.config, self.logger,
                start_serial=start_serial
            )
            
            result_info['events'] = result.events
            result_info['last_serial'] = result.last_serial
            result_info['completed'] = result.completed
            
        except Exception as e:
            result_info['error'] = str(e)
            self.logger.error(f"    [ERROR] {name}: {e}")
        
        return result_info
    
    def collect_once(self) -> int:
        """Однократный сбор со всех устройств (параллельно)"""
        output_file = self.config['output_file']
        devices = self.config.get('devices', [])
        max_workers = self.config.get('max_parallel', 4)
        
        active_devices = [d for d in devices if d.get('enabled', True)]
        self.logger.info(f"🔄 Начало сбора ({len(active_devices)} устройств)")
        
        end_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        
        # Создаём директорию если нужно
        output_dir = os.path.dirname(output_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # Параллельный сбор с устройств
        results: List[Dict[str, Any]] = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    self._collect_from_device, device, end_time
                ): device
                for device in active_devices
            }
            
            for future in as_completed(futures):
                try:
                    result_info = future.result()
                    results.append(result_info)
                except Exception as e:
                    device = futures[future]
                    self.logger.error(f"    [ERROR] {device['host']}: {e}")
        
        # Записываем собранные события в файл (последовательно)
        total_new = 0
        total_dup = 0
        
        with open(output_file, 'a', encoding='utf-8') as f:
            for r in results:
                if r.get('error') or 'events' not in r:
                    continue
                
                host = r['host']
                name = r['name']
                new_count = 0
                dup_count = 0
                
                for event in r['events']:
                    serial = event.get('serialNo')
                    if serial and self.tracker.is_duplicate(host, serial):
                        dup_count += 1
                        continue
                    
                    # Добавляем метаданные
                    event['_device'] = host
                    event['_device_name'] = name
                    event['_collected'] = datetime.now().isoformat()
                    
                    f.write(json.dumps(event, ensure_ascii=False) + '\n')
                    new_count += 1
                
                total_new += new_count
                total_dup += dup_count
                
                # Обновляем состояние
                last_serial = r.get('last_serial', 0)
                if last_serial > 0:
                    self.tracker.update_last_serial(host, last_serial)
                
                # Обновляем время только если дошли до конца
                if r['completed']:
                    self.tracker.update_last_collect(host, end_time)
                    status = "✅"
                else:
                    status = "⚠️"
                
                self.logger.info(
                    f"    [{status}] {name}: {new_count} новых, "
                    f"{dup_count} дубликатов"
                )
        
        self.logger.info(
            f"📊 Итого: {total_new} новых, {total_dup} дубликатов"
        )
        return total_new
    
    def run_loop(self) -> None:
        """Запуск в режиме демона"""
        interval = self.config.get('interval_minutes', 15) * 60
        
        self.logger.info(f"🚀 Запуск сборщика (интервал: {interval//60} мин)")
        
        while not self.stop_event.is_set():
            try:
                self.collect_once()
            except Exception as e:
                self.logger.error(f"[ERROR] Критическая ошибка: {e}")
            
            # Ждём следующего интервала
            self.logger.info(f"💤 Следующий сбор через {interval//60} минут")
            self.stop_event.wait(interval)
        
        self.logger.info("🛑 Сборщик остановлен")
    
    def stop(self) -> None:
        """Остановка сборщика"""
        self.stop_event.set()


# ============================================================================
# WINDOWS СЛУЖБА
# ============================================================================

if HAS_WIN32:
    class CollectorService(win32serviceutil.ServiceFramework):
        _svc_name_ = "LogStormCollector"
        _svc_display_name_ = "LogStorm Event Collector"
        _svc_description_ = "Собирает события СКУД с устройств Hikvision/HiWatch"
        
        def __init__(self, args):
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.stop_event = win32event.CreateEvent(None, 0, 0, None)
            self.collector = None
        
        def SvcStop(self):
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            win32event.SetEvent(self.stop_event)
            if self.collector:
                self.collector.stop()
        
        def SvcDoRun(self):
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, '')
            )
            self.main()
        
        def main(self):
            # Путь к конфигу рядом с исполняемым файлом
            script_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(script_dir, 'collector.json')
            
            config = load_config(config_path)
            log_file = config.get('log_file', 'collector.log')
            if not os.path.isabs(log_file):
                log_file = os.path.join(script_dir, log_file)
            
            logger = setup_logging(log_file)
            
            self.collector = Collector(config, logger)
            self.collector.run_loop()


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="LogStorm Collector - Сборщик событий СКУД"
    )
    
    parser.add_argument('--config', '-c', default='collector.json',
                        help='Путь к конфигурации')
    parser.add_argument('--once', action='store_true',
                        help='Однократный сбор и выход')
    parser.add_argument('--init', action='store_true',
                        help='Создать пример конфигурации')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Подробный вывод')
    
    # Команды Windows службы
    if HAS_WIN32:
        parser.add_argument('command', nargs='?',
                            choices=['install', 'remove', 'start', 'stop', 'restart'],
                            help='Управление Windows службой')
    
    args = parser.parse_args()
    
    # Создание конфига
    if args.init:
        save_default_config(args.config)
        return
    
    # Windows служба
    if HAS_WIN32 and args.command:
        if args.command == 'install':
            win32serviceutil.InstallService(
                CollectorService._svc_reg_class_,
                CollectorService._svc_name_,
                CollectorService._svc_display_name_
            )
            print("[OK] Служба установлена")
        elif args.command == 'remove':
            win32serviceutil.RemoveService(CollectorService._svc_name_)
            print("[OK] Служба удалена")
        elif args.command == 'start':
            win32serviceutil.StartService(CollectorService._svc_name_)
            print("[OK] Служба запущена")
        elif args.command == 'stop':
            win32serviceutil.StopService(CollectorService._svc_name_)
            print("[OK] Служба остановлена")
        elif args.command == 'restart':
            win32serviceutil.RestartService(CollectorService._svc_name_)
            print("[OK] Служба перезапущена")
        return
    
    # Загрузка конфигурации
    if not os.path.exists(args.config):
        print(f"[ERROR] Файл конфигурации не найден: {args.config}")
        print(f"        Создайте его командой: python collector.py --init")
        sys.exit(1)
    
    config = load_config(args.config)
    logger = setup_logging(
        config.get('log_file', 'collector.log'),
        args.verbose
    )
    
    collector = Collector(config, logger)
    
    # Обработка Ctrl+C
    def signal_handler(sig, frame):
        print("\n[!] Получен сигнал остановки...")
        collector.stop()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    if args.once:
        collector.collect_once()
    else:
        collector.run_loop()


if __name__ == "__main__":
    main()
