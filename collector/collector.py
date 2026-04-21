#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LogStorm Collector - Фоновый сборщик событий СКУД

Собирает события с нескольких Hikvision камер по расписанию.
Запускается через systemd (Linux) или планировщик задач (Windows).

Возможности:
  - Параллельный сбор с нескольких устройств (max_parallel)
  - Двойное хранилище: NDJSON + SQLite
  - Состояние в SQLite (защита от рассинхрона)
  - Дедупликация по PRIMARY KEY и кэш в памяти
  - Индивидуальные настройки изображений для каждой камеры

Использование:
  # Однократный сбор
  python collector.py --once --verbose

  # Запуск в режиме демона (каждые N минут)
  python collector.py --config collector.json

  # Создать пример конфигурации
  python collector.py --init
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

import requests
from requests.auth import HTTPDigestAuth
from requests.exceptions import ConnectionError, ReadTimeout

try:
    from .storage import EventStorage
except ImportError:  # pragma: no cover - direct script execution
    from storage import EventStorage

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


def get_app_dir() -> str:
    """Получить директорию приложения (работает и для PyInstaller)"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def save_default_config(config_path: str) -> None:
    """Сохранение конфигурации по умолчанию"""
    # Если путь относительный, сохраняем рядом с exe
    if not os.path.isabs(config_path):
        config_path = os.path.join(get_app_dir(), config_path)
    
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
    """Трекер состояния сбора событий с устройств"""
    
    def __init__(self, storage: 'EventStorage', initial_days: int = 30):
        """
        Args:
            storage: Хранилище для работы с БД и NDJSON
            initial_days: Период первоначального сбора (дней назад)
        """
        self.storage = storage
        self.initial_days = initial_days
        # In-memory кэш для быстрой проверки дубликатов
        self._serials: Dict[str, Set[int]] = {}
    
    def is_duplicate(self, device: str, serial: int) -> bool:
        """Быстрая проверка дубликата по serialNo в памяти"""
        if device not in self._serials:
            self._serials[device] = set()
        
        if serial in self._serials[device]:
            return True
        
        # Добавляем в кэш
        self._serials[device].add(serial)
        
        # Ограничиваем размер кэша для экономии памяти
        MAX_CACHE_SIZE = 10000
        CACHE_TRIM_SIZE = 5000
        
        if len(self._serials[device]) > MAX_CACHE_SIZE:
            # Оставляем только последние serial (предположительно новые)
            sorted_serials = sorted(self._serials[device])
            self._serials[device] = set(sorted_serials[-CACHE_TRIM_SIZE:])
        
        return False
    
    def get_last_collect_time(self, device: str) -> Optional[str]:
        """Получить время последнего успешного сбора из БД"""
        state = self.storage.get_collector_state(device)
        return state['last_collect'] if state else None
    
    def get_last_serial(self, device: str) -> int:
        """Получить последний собранный serialNo из БД"""
        state = self.storage.get_collector_state(device)
        if state and state['last_serial']:
            return state['last_serial']
        # Fallback: проверяем события напрямую
        return self.storage.get_last_serial(device)
    
    def update_last_serial(self, device: str, serial: int) -> None:
        """Обновить последний успешный serialNo"""
        state = self.storage.get_collector_state(device)
        last_collect = state['last_collect'] if state else None
        self.storage.update_collector_state(device, serial, last_collect)
    
    def update_last_collect(self, device: str, timestamp: str) -> None:
        """Обновить время последнего сбора"""
        last_serial = self.get_last_serial(device)
        self.storage.update_collector_state(device, last_serial, timestamp)
    
    def get_start_time(self, device: str) -> str:
        """Определить время начала для следующего сбора"""
        last = self.get_last_collect_time(device)
        
        if last:
            # Начинаем за 1 час до последнего (перекрытие для надёжности)
            try:
                dt = datetime.fromisoformat(last.replace('Z', '+00:00'))
                dt = dt - timedelta(hours=1)
                return dt.strftime("%Y-%m-%dT%H:%M:%S")
            except ValueError:
                pass
        
        # Первый запуск: берём период из конфига
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
    last_event_time: Optional[str] = None  # Время последнего события


def save_image(
    image_data: bytes,
    event: Dict[str, Any],
    images_config: Dict[str, Any],
    logger: logging.Logger
) -> Optional[str]:
    """Сохранение изображения события"""
    folder = images_config.get('folder', 'images')
    fmt = images_config.get(
        'format', '{date}/{employeeNoString}_{serialNo}.jpg'
    )
    
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


def download_image(
    pic_url: str,
    auth: HTTPDigestAuth,
    session: requests.Session,
    logger: logging.Logger,
    timeout: int = 10
) -> Optional[bytes]:
    """Скачивание изображения по HTTP URL из pictureURL"""
    try:
        resp = session.get(pic_url, auth=auth, timeout=timeout)
        if resp.status_code == 200:
            ct = resp.headers.get('Content-Type', '')
            if 'image' in ct:
                return resp.content
            else:
                logger.debug(f"    [WARN] pictureURL не изображение: {ct}")
        else:
            logger.debug(f"    [WARN] pictureURL HTTP {resp.status_code}")
    except Exception as e:
        logger.debug(f"    [WARN] Ошибка скачивания: {e}")
    return None


def build_request_conditions(
    start_time: str,
    end_time: str,
    next_serial: int,
    config: Dict[str, Any],
    save_images: bool
) -> Dict[str, Any]:
    """Построение условий запроса к ISAPI"""
    req = config.get('request', {})
    
    # Расширяем endTime на +1 день для serial-based навигации
    extended_end_time = (
        datetime.fromisoformat(end_time.replace('T', ' ')) + timedelta(days=1)
    ).strftime("%Y-%m-%dT%H:%M:%S")
    
    return {
        "searchID": "collector",
        "searchResultPosition": 0,
        "maxResults": req.get('page_size', 30),
        "major": req.get('major', 5),
        "minor": req.get('minor', 0),
        "startTime": start_time,
        "endTime": extended_end_time,
        "picEnable": save_images,
        "timeReverseOrder": False,
        "beginSerialNo": next_serial,
        "endSerialNo": 999999999,
    }


def parse_multipart_response(
    resp: requests.Response,
    save_images: bool,
    logger: logging.Logger,
    device_name: str
) -> tuple[Optional[Dict[str, Any]], Dict[str, bytes]]:
    """
    Парсинг multipart ответа от камеры
    
    Returns:
        (payload, images_data): JSON данные и словарь изображений
    """
    if MultipartDecoder is None:
        logger.error(
            f"    [{device_name}][ERROR] Нужен requests-toolbelt "
            "для multipart"
        )
        return None, {}
    
    dec = MultipartDecoder(
        resp.content, resp.headers.get("Content-Type", "")
    )
    
    payload = None
    images_data: Dict[str, bytes] = {}
    
    for part in dec.parts:
        pct = part.headers.get(b"Content-Type", b"")
        
        if b"application/json" in pct:
            payload = json.loads(part.content.decode("utf-8", "ignore"))
        
        elif b"image/" in pct and save_images:
            # Извлекаем Content-ID для связи с событием
            cid = part.headers.get(b"Content-ID", b"")
            if isinstance(cid, bytes):
                cid = cid.decode("utf-8", "ignore")
            cid = cid.strip("<>")
            if cid:
                images_data[cid] = part.content
    
    return payload, images_data


def process_event_images(
    events: List[Dict[str, Any]],
    images_data: Dict[str, bytes],
    images_cfg: Dict[str, Any],
    auth: HTTPDigestAuth,
    session: requests.Session,
    logger: logging.Logger
) -> int:
    """
    Обработка и сохранение изображений для событий
    
    Returns:
        Количество сохранённых изображений
    """
    images_saved = 0
    
    # Сначала пытаемся из multipart (если есть)
    if images_data:
        for event in events:
            pic_url = event.get("pictureURL", "")
            if pic_url and pic_url in images_data:
                img_path = save_image(
                    images_data[pic_url], event, images_cfg, logger
                )
                if img_path:
                    event["_imagePath"] = img_path
                    images_saved += 1
    
    # Если нет multipart, скачиваем по HTTP из pictureURL
    else:
        for event in events:
            pic_url = event.get("pictureURL", "")
            if pic_url:
                img_data = download_image(pic_url, auth, session, logger)
                if img_data:
                    img_path = save_image(
                        img_data, event, images_cfg, logger
                    )
                    if img_path:
                        event["_imagePath"] = img_path
                        images_saved += 1
    
    return images_saved


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
    device_name = device.get('name', host)
    user = device['user']
    password = device['password']
    req = config.get('request', {})
    images_cfg = config.get('images', {})
    
    # Индивидуальная настройка для устройства или глобальная
    save_images = device.get('save_images', images_cfg.get('enabled', False))
    
    base_url = f"http://{host}"
    auth = HTTPDigestAuth(user, password)
    
    session = requests.Session()
    session.headers.update({"Accept": "application/json"})
    
    all_events: List[Dict[str, Any]] = []
    last_successful_serial = start_serial
    iteration = 0
    completed = True
    images_saved = 0
    
    logger.debug(f"    [{device_name}] Период: {start_time} -> {end_time}")
    logger.debug(f"    [{device_name}] Начальный serial: {start_serial}")
    if save_images:
        logger.debug(
            f"    [{device_name}] Сохранение изображений: "
            f"{images_cfg.get('folder')}"
        )
    
    # Serial-based навигация (beginSerialNo)
    next_serial = start_serial
    
    while True:
        iteration += 1
        
        # Построение условий запроса
        cond = build_request_conditions(
            start_time, end_time, next_serial, config, save_images
        )
        
        url = f"{base_url}/ISAPI/AccessControl/AcsEvent?format=json"
        
        logger.debug(
            f"    [{device_name}][{iteration}] serial from {next_serial}..."
        )
        
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
            logger.debug(
                f"    [{device_name}][{iteration}] "
                f"{req_elapsed:.1f}с, HTTP {status}"
            )
            
            if status == 401:
                logger.error(f"    [{device_name}][ERROR] Авторизация (401)")
                completed = False
                break
            
            if status >= 400:
                logger.error(f"    [{device_name}][ERROR] HTTP {status}")
                completed = False
                break
            
            # Парсинг JSON и изображений
            ct = (resp.headers.get("Content-Type") or "").lower()
            
            if "multipart" in ct:
                payload, images_data = parse_multipart_response(
                    resp, save_images, logger, device_name
                )
                if payload is None:
                    logger.error(
                        f"    [{device_name}][ERROR] Multipart без JSON"
                    )
                    completed = False
                    break
            else:
                payload = resp.json()
                images_data = {}
            
            # Проверка ошибки устройства
            if "statusCode" in payload:
                msg = payload.get('statusString', 'unknown')
                logger.error(f"    [{device_name}][ERROR] Устройство: {msg}")
                completed = False
                break
            
            # Извлечение событий
            acs = payload.get("AcsEvent", {})
            events = acs.get("InfoList", [])
            
            logger.debug(
                f"    [{device_name}][{iteration}] +{len(events)} событий"
            )
            
            if not events:
                break
            
            # Сохранение изображений (если включено)
            if save_images:
                saved = process_event_images(
                    events, images_data, images_cfg, auth, session, logger
                )
                images_saved += saved
            
            all_events.extend(events)
            
            # Обновляем указатель на следующий serial
            max_sn = max((e.get("serialNo", 0) for e in events), default=0)
            if max_sn > 0:
                last_successful_serial = max_sn
                next_serial = max_sn + 1
            
            logger.debug(
                f"    [{device_name}][{iteration}] Всего: {len(all_events)}, "
                f"next_serial: {next_serial}"
            )
            
            # Условие остановки: пустой ответ означает конец данных
            if len(events) == 0:
                break
                
        except (ReadTimeout, ConnectionError) as e:
            error_type = (
                "Таймаут" if isinstance(e, ReadTimeout)
                else "Ошибка соединения"
            )
            logger.warning(f"    [{device_name}][WARN] {error_type}: {e}")
            completed = False
            break
        except Exception as e:
            logger.error(
                f"    [{device_name}][ERROR] {type(e).__name__}: {e}"
            )
            completed = False
            break
    
    session.close()
    
    # Получаем время последнего события
    last_event_time = None
    if all_events:
        # События должны быть отсортированы по времени
        last_event_time = all_events[-1].get('time')
    
    if save_images and images_saved > 0:
        logger.debug(
            f"    [{device_name}] Сохранено изображений: {images_saved}"
        )
    
    logger.debug(
        f"    [{device_name}] Итого: {len(all_events)} событий, "
        f"serial: {start_serial} -> {last_successful_serial}"
    )
    return FetchResult(
        all_events, last_successful_serial, completed, last_event_time
    )


# ============================================================================
# СБОРЩИК
# ============================================================================

class Collector:
    """Основной класс сборщика событий СКУД"""
    
    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        self.config = config
        self.logger = logger
        initial_days = config.get('initial_days', 30)
        
        # Определение путей к файлам хранилища
        storage_config = config.get('storage', {})
        
        # NDJSON файл (новый формат: storage.ndjson, старый: output_file)
        ndjson_file = (
            storage_config.get('ndjson') or config.get('output_file')
        )
        if not ndjson_file:
            raise ValueError(
                "Не указан путь к NDJSON файлу. "
                "Используйте storage.ndjson или output_file"
            )
        
        if not os.path.isabs(ndjson_file):
            ndjson_file = os.path.join(get_app_dir(), ndjson_file)
        
        # SQLite файл (новый формат: storage.sqlite, старый: sqlite_file)
        sqlite_file = (
            storage_config.get('sqlite') or config.get('sqlite_file')
        )
        if sqlite_file and not os.path.isabs(sqlite_file):
            sqlite_file = os.path.join(get_app_dir(), sqlite_file)
        
        # Инициализация хранилища и трекера
        self.ndjson_file = ndjson_file
        self.sqlite_file = sqlite_file
        self.storage = EventStorage(ndjson_file, sqlite_file)
        self.tracker = EventTracker(self.storage, initial_days)
        
        self.stop_event = Event()
        self._file_lock = Lock()
    
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
            result_info['last_event_time'] = result.last_event_time
            
        except Exception as e:
            result_info['error'] = str(e)
            self.logger.error(f"    [ERROR] {name}: {e}")
        
        return result_info
    
    def collect_once(self) -> int:
        """Однократный сбор со всех устройств (параллельно)"""
        # Используем self.ndjson_file (уже инициализирован в __init__)
        output_file = self.ndjson_file
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
        
        # Записываем собранные события (в NDJSON + SQLite)
        total_new = 0
        total_dup = 0
        
        for r in results:
            if r.get('error') or 'events' not in r:
                continue
            
            host = r['host']
            name = r['name']
            
            # In-memory кэш дубликатов живёт только в рамках процесса.
            # Для корректной инкрементальной загрузки (особенно overlap -1h)
            # опираемся на last_serial из SQLite.
            last_serial_state = self.tracker.get_last_serial(host)
            new_count = 0
            dup_count = 0
            events_to_write = []
            
            for event in r['events']:
                serial = event.get('serialNo')

                # Пропускаем события без serialNo
                if serial is None:
                    dup_count += 1
                    continue

                # Фильтр по БД: события с serial <= last_serial_state
                # уже были собраны ранее
                if int(serial) <= int(last_serial_state):
                    dup_count += 1
                    continue

                # Дополнительная защита от дубликатов в текущей сессии
                if self.tracker.is_duplicate(host, int(serial)):
                    dup_count += 1
                    continue
                
                # Добавляем метаданные
                event['_device'] = host
                event['_device_name'] = name
                event['_collected'] = datetime.now().isoformat()
                
                events_to_write.append(event)
                new_count += 1
            
            # Запись в оба хранилища (NDJSON + SQLite)
            if events_to_write:
                self.storage.write_events(events_to_write)
            
            total_new += new_count
            total_dup += dup_count
            
            # Обновляем состояние
            last_serial = r.get('last_serial', 0)
            if last_serial > 0:
                self.tracker.update_last_serial(host, last_serial)
            
            # Обновляем время на время ПОСЛЕДНЕГО СОБЫТИЯ (не now!)
            # Это предотвращает пропуски при следующем запуске
            if r['completed']:
                # Используем время последнего события если есть
                update_time = r.get('last_event_time') or end_time
                self.tracker.update_last_collect(host, update_time)
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
    
    args = parser.parse_args()
    
    # Создание конфига
    if args.init:
        save_default_config(args.config)
        return
    
    # Определяем путь к конфигу
    config_path = args.config
    if not os.path.isabs(config_path):
        config_path = os.path.join(get_app_dir(), config_path)
    
    # Загрузка конфигурации
    if not os.path.exists(config_path):
        print(f"[ERROR] Файл конфигурации не найден: {config_path}")
        print("        Создайте его командой: LogStormCollector.exe --init")
        sys.exit(1)
    
    config = load_config(config_path)
    
    # Лог-файл рядом с exe если путь относительный
    log_file = config.get('log_file', 'collector.log')
    if not os.path.isabs(log_file):
        log_file = os.path.join(get_app_dir(), log_file)
    
    logger = setup_logging(log_file, args.verbose)
    
    collector = Collector(config, logger)
    
    # Обработка Ctrl+C (двойное нажатие для принудительной остановки)
    ctrl_c_count = [0]
    
    def signal_handler(sig, frame):
        ctrl_c_count[0] += 1
        if ctrl_c_count[0] == 1:
            print(
                "\n[!] Получен сигнал остановки... "
                "(Ctrl+C ещё раз для немедленной остановки)"
            )
            collector.stop()
        else:
            print("\n[!] Принудительная остановка!")
            sys.exit(1)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    if args.once:
        collector.collect_once()
    else:
        collector.run_loop()


if __name__ == "__main__":
    main()
