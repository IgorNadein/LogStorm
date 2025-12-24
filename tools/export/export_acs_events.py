#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Export Hikvision/HiWatch AccessControl events via ISAPI.

Единый скрипт экспорта событий СКУД с поддержкой:
  - Экспорт за один период
  - Экспорт с разбиением на части (--chunk-days)
  - Защита от перезаписи файлов
  - Дедупликация событий
  - Продолжение прерванного экспорта

Примеры:
  # Простой экспорт
  python export_events.py --password CHANGE_ME --end 2025-12-31T23:59:59

  # Экспорт большого периода с разбиением по 30 дней
  python export_events.py --password CHANGE_ME \\
    --start 2024-01-01 --end 2024-12-31 --chunk-days 30

Dependencies:
  pip install requests requests-toolbelt
"""

import argparse
import json
import os
import sys
import time
import hashlib
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Dict, List, Optional, Set, Tuple

import requests
from requests.auth import HTTPDigestAuth
from requests.exceptions import ConnectionError, ReadTimeout

try:
    from requests_toolbelt.multipart.decoder import MultipartDecoder
except Exception:  # pragma: no cover
    MultipartDecoder = None  # type: ignore


# ============================================================================
# УТИЛИТЫ
# ============================================================================

_timing_stats: Dict[str, Dict[str, Any]] = {}


def timeit(func):
    """Декоратор для замера времени выполнения"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed = time.perf_counter() - start
            name = func.__name__
            if name not in _timing_stats:
                _timing_stats[name] = {
                    'calls': 0, 'total': 0.0,
                    'min': float('inf'), 'max': 0.0
                }
            s = _timing_stats[name]
            s['calls'] += 1
            s['total'] += elapsed
            s['min'] = min(s['min'], elapsed)
            s['max'] = max(s['max'], elapsed)
    return wrapper


def print_timing_stats() -> None:
    """Вывод статистики времени"""
    if not _timing_stats:
        return
    print("\n" + "=" * 70)
    print("⏱️  СТАТИСТИКА ВРЕМЕНИ")
    print("=" * 70)
    for name, s in sorted(_timing_stats.items(), 
                          key=lambda x: x[1]['total'], reverse=True):
        avg = s['total'] / s['calls'] if s['calls'] else 0
        print(f"{name:<25} {s['calls']:>5} вызовов, "
              f"{s['total']:>8.2f}с всего, {avg:.3f}с среднее")


def ensure_dir(path: str) -> None:
    """Создание директории"""
    if path:
        os.makedirs(path, exist_ok=True)


def get_safe_filepath(filepath: str, force: bool = False) -> str:
    """Получить безопасный путь (без перезаписи существующего)"""
    if force or not os.path.exists(filepath):
        return filepath
    
    base, ext = os.path.splitext(filepath)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_path = f"{base}_{ts}{ext}"
    
    counter = 1
    while os.path.exists(new_path):
        new_path = f"{base}_{ts}_{counter}{ext}"
        counter += 1
    
    print(f"⚠️  Файл существует, используем: {new_path}")
    return new_path


def backup_file(filepath: str) -> Optional[str]:
    """Создать резервную копию файла"""
    if not os.path.exists(filepath):
        return None
    
    import shutil
    backup = f"{filepath}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(filepath, backup)
    print(f"📦 Резервная копия: {backup}")
    return backup


# ============================================================================
# ДЕДУПЛИКАЦИЯ
# ============================================================================

class Deduplicator:
    """Дедупликация событий по serialNo"""
    
    def __init__(self):
        self._serials: Set[int] = set()
        self._hashes: Set[str] = set()
        self.duplicates = 0
        self.processed = 0
    
    def is_duplicate(self, event: Dict[str, Any]) -> bool:
        """Проверка дубликата"""
        self.processed += 1
        
        serial = event.get('serialNo')
        if isinstance(serial, int):
            if serial in self._serials:
                self.duplicates += 1
                return True
            self._serials.add(serial)
            return False
        
        # Fallback на хэш
        h = hashlib.md5(
            json.dumps(event, sort_keys=True).encode()
        ).hexdigest()
        if h in self._hashes:
            self.duplicates += 1
            return True
        self._hashes.add(h)
        return False
    
    def load_from_file(self, filepath: str) -> int:
        """Загрузить существующие события"""
        if not os.path.exists(filepath):
            return 0
        
        count = 0
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    serial = event.get('serialNo')
                    if isinstance(serial, int):
                        self._serials.add(serial)
                    count += 1
                except json.JSONDecodeError:
                    pass
        return count
    
    def get_max_serial(self) -> Optional[int]:
        """Получить максимальный serialNo"""
        return max(self._serials) if self._serials else None
    
    def print_stats(self) -> None:
        """Вывод статистики"""
        if self.duplicates > 0:
            pct = (self.duplicates / self.processed * 100) if self.processed else 0
            print(f"📊 Дедупликация: {self.duplicates} дубликатов "
                  f"из {self.processed} ({pct:.1f}%)")


# ============================================================================
# ISAPI КЛИЕНТ
# ============================================================================

@timeit
def extract_events(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Извлечь события из ответа"""
    acs = payload.get("AcsEvent")
    if isinstance(acs, dict):
        info = acs.get("InfoList")
        if isinstance(info, list):
            return [x for x in info if isinstance(x, dict)]
    return []


def is_device_error(payload: Dict[str, Any]) -> bool:
    """Проверка ошибки устройства"""
    return (isinstance(payload, dict) and 
            "statusCode" in payload and "statusString" in payload)


@timeit
def parse_response(
    resp: requests.Response,
    save_images: bool,
    img_dir: Optional[str],
    img_prefix: str,
) -> Tuple[Dict[str, Any], List[str]]:
    """Парсинг ответа (JSON или multipart)"""
    ct = (resp.headers.get("Content-Type") or "").lower()
    saved: List[str] = []

    if "multipart" in ct:
        if MultipartDecoder is None:
            raise RuntimeError(
                "Multipart response requires requests-toolbelt. "
                "Install: pip install requests-toolbelt"
            )

        dec = MultipartDecoder(resp.content, 
                               resp.headers.get("Content-Type", ""))

        json_part = None
        for part in dec.parts:
            pct = part.headers.get(b"Content-Type", b"").decode().lower()
            if "application/json" in pct:
                json_part = part
                break

        if json_part is None:
            raise RuntimeError("Multipart without JSON part")

        payload = json.loads(json_part.content.decode("utf-8", "ignore"))

        if save_images and img_dir:
            ensure_dir(img_dir)
            # Извлекаем изображения из multipart по Content-ID
            images_by_cid: Dict[str, bytes] = {}
            for part in dec.parts:
                pct = part.headers.get(b"Content-Type", b"").decode().lower()
                if "image/jpeg" in pct:
                    cid = part.headers.get(b"Content-ID", b"").decode().strip("<>")
                    if cid:
                        images_by_cid[cid] = part.content
            
            # Связываем изображения с событиями по pictureURL
            events = extract_events(payload)
            for event in events:
                pic_url = event.get("pictureURL", "")
                if pic_url in images_by_cid:
                    serial = event.get("serialNo", 0)
                    fpath = os.path.join(img_dir, f"{img_prefix}_s{serial}.jpg")
                    with open(fpath, "wb") as f:
                        f.write(images_by_cid[pic_url])
                    saved.append(fpath)

        return payload, saved

    if "json" not in ct:
        raise RuntimeError(f"Non-JSON response: {resp.text[:300]}")

    return resp.json(), saved


def download_image_from_url(
    pic_url: str,
    auth: HTTPDigestAuth,
    session: requests.Session,
    timeout: int = 10
) -> Optional[bytes]:
    """Скачивание изображения по HTTP URL из pictureURL"""
    try:
        resp = session.get(pic_url, auth=auth, timeout=timeout)
        if resp.status_code == 200:
            ct = resp.headers.get('Content-Type', '')
            if 'image' in ct:
                return resp.content
    except Exception:
        pass
    return None


@timeit
def fetch_events(
    session: requests.Session,
    base_url: str,
    auth: HTTPDigestAuth,
    cond: Dict[str, Any],
    timeout: int,
    retries: int,
    save_images: bool,
    img_dir: Optional[str],
    img_prefix: str,
) -> Tuple[Dict[str, Any], List[str], requests.Session]:
    """Запрос событий с повторами"""
    url = f"{base_url}/ISAPI/AccessControl/AcsEvent?format=json"
    
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            resp = session.post(
                url, auth=auth,
                json={"AcsEventCond": cond},
                timeout=(5, timeout)
            )
            
            if resp.status_code == 401:
                raise RuntimeError(f"Unauthorized (401)")
            if resp.status_code >= 400:
                raise RuntimeError(f"HTTP {resp.status_code}")

            payload, saved = parse_response(
                resp, save_images, img_dir, img_prefix
            )
            
            if is_device_error(payload):
                raise RuntimeError(f"Device error: {payload}")

            return payload, saved, session

        except (ReadTimeout, ConnectionError) as e:
            last_err = e
            time.sleep(attempt)
            session.close()
            session = requests.Session()
            session.headers.update({"Accept": "application/json"})
            continue

    raise RuntimeError(f"Failed after {retries} retries: {last_err}")


# ============================================================================
# ЭКСПОРТЕР
# ============================================================================

class EventExporter:
    """Экспортер событий СКУД"""
    
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.session: Optional[requests.Session] = None
        self.auth: Optional[HTTPDigestAuth] = None
        self.dedup: Optional[Deduplicator] = None
        
        self.total_exported = 0
        self.output_path = ""
    
    def setup(self) -> None:
        """Инициализация"""
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        self.auth = HTTPDigestAuth(self.args.user, self.args.password)
        
        # Определение выходного файла
        if self.args.append and os.path.exists(self.args.out):
            self.output_path = self.args.out
            print(f"📎 Дополнение: {self.output_path}")
        else:
            self.output_path = get_safe_filepath(
                self.args.out, self.args.force
            )
        
        # Резервная копия
        if self.args.backup and os.path.exists(self.output_path):
            backup_file(self.output_path)
        
        # Дедупликация
        if self.args.deduplicate or self.args.append or self.args.resume:
            self.dedup = Deduplicator()
            if os.path.exists(self.output_path):
                loaded = self.dedup.load_from_file(self.output_path)
                if loaded:
                    print(f"📊 Загружено {loaded} событий для дедупликации")
    
    def get_start_serial(self) -> int:
        """Начальный serialNo"""
        if self.args.resume and self.dedup:
            last = self.dedup.get_max_serial()
            if last:
                print(f"▶️  Продолжение с serialNo: {last + 1}")
                return last + 1
        return self.args.begin_serial
    
    def export_period(
        self, 
        start_time: str, 
        end_time: str,
        file_handle
    ) -> int:
        """Экспорт одного периода"""
        base_url = f"http://{self.args.host}"
        save_images = self.args.pic and not self.args.no_save_images
        img_dir = self.args.img_dir if save_images else None
        
        next_serial = self.get_start_serial()
        period_exported = 0
        
        while True:
            cond = {
                "searchID": "export",
                "searchResultPosition": 0,
                "maxResults": self.args.page,
                "major": self.args.major,
                "minor": self.args.minor,
                "startTime": start_time,
                "endTime": end_time,
                "picEnable": self.args.pic,
                "timeReverseOrder": False,
                "beginSerialNo": next_serial,
                "endSerialNo": self.args.end_serial,
            }
            
            payload, _, self.session = fetch_events(
                self.session, base_url, self.auth, cond,
                self.args.timeout, self.args.retries,
                save_images, img_dir, f"s{next_serial}"
            )
            
            events = extract_events(payload)
            if not events:
                break
            
            # Скачивание изображений из pictureURL (если не multipart)
            if save_images and img_dir:
                ensure_dir(img_dir)
                for e in events:
                    pic_url = e.get("pictureURL", "")
                    if pic_url and pic_url.startswith("http"):
                        img_data = download_image_from_url(
                            pic_url, self.auth, self.session
                        )
                        if img_data:
                            serial = e.get("serialNo", 0)
                            fpath = os.path.join(
                                img_dir, f"s{next_serial}_sn{serial}.jpg"
                            )
                            with open(fpath, "wb") as f:
                                f.write(img_data)
            
            max_sn = None
            for e in events:
                if self.dedup and self.dedup.is_duplicate(e):
                    continue
                
                file_handle.write(json.dumps(e, ensure_ascii=False) + "\n")
                self.total_exported += 1
                period_exported += 1
                
                sn = e.get("serialNo")
                if isinstance(sn, int):
                    max_sn = sn if max_sn is None else max(max_sn, sn)
            
            if max_sn is None:
                break
            
            next_serial = max_sn + 1
            
            sys.stderr.write(f"\r  Экспортировано: {period_exported}")
            sys.stderr.flush()
            
            if len(events) < self.args.page:
                break
            
            if self.args.sleep > 0:
                time.sleep(self.args.sleep)
        
        sys.stderr.write("\n")
        return period_exported
    
    def run(self) -> int:
        """Запуск экспорта"""
        self.setup()
        
        mode = "a" if self.args.append else "w"
        
        # Определяем периоды
        if self.args.chunk_days and self.args.chunk_days > 0:
            periods = self._calculate_chunks()
            print(f"📅 Разбиение на {len(periods)} периодов "
                  f"по {self.args.chunk_days} дней")
        else:
            periods = [(self.args.start, self.args.end)]
        
        with open(self.output_path, mode, encoding="utf-8") as f:
            for i, (start, end) in enumerate(periods, 1):
                if len(periods) > 1:
                    print(f"\n[{i}/{len(periods)}] {start[:10]} → {end[:10]}")
                
                exported = self.export_period(start, end, f)
                
                if len(periods) > 1:
                    print(f"  ✅ {exported} событий")
        
        self._print_summary()
        return self.total_exported
    
    def _calculate_chunks(self) -> List[Tuple[str, str]]:
        """Разбиение периода на части"""
        # Парсим даты
        start_str = self.args.start
        end_str = self.args.end
        
        # Убираем время если есть
        if 'T' in start_str:
            start_date = datetime.fromisoformat(start_str.replace('Z', ''))
        else:
            start_date = datetime.strptime(start_str, "%Y-%m-%d")
        
        if 'T' in end_str:
            end_date = datetime.fromisoformat(end_str.replace('Z', ''))
        else:
            end_date = datetime.strptime(end_str, "%Y-%m-%d")
            end_date = end_date.replace(hour=23, minute=59, second=59)
        
        chunks = []
        current = start_date
        
        while current < end_date:
            chunk_end = min(
                current + timedelta(days=self.args.chunk_days),
                end_date
            )
            chunks.append((
                current.strftime("%Y-%m-%dT%H:%M:%S"),
                chunk_end.strftime("%Y-%m-%dT%H:%M:%S")
            ))
            current = chunk_end
        
        return chunks
    
    def _print_summary(self) -> None:
        """Вывод итогов"""
        print(f"\n✅ Экспортировано: {self.total_exported} событий")
        print(f"   Файл: {self.output_path}")
        
        if self.dedup:
            self.dedup.print_stats()
        
        if self.args.verbose:
            print_timing_stats()


# ============================================================================
# CLI
# ============================================================================

def create_parser() -> argparse.ArgumentParser:
    """Создание парсера аргументов"""
    p = argparse.ArgumentParser(
        description="Экспорт событий СКУД Hikvision/HiWatch в NDJSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  # Базовый экспорт
  python export_events.py --password CHANGE_ME --end 2025-12-31T23:59:59

  # С разбиением на периоды по 30 дней
  python export_events.py --password CHANGE_ME \\
    --start 2024-01-01 --end 2024-12-31 --chunk-days 30

  # Дополнение существующего файла
  python export_events.py --password CHANGE_ME --end 2025-12-31T23:59:59 --append

  # Продолжение прерванного экспорта
  python export_events.py --password CHANGE_ME --end 2025-12-31T23:59:59 --resume
        """
    )
    
    # Подключение
    g = p.add_argument_group('Подключение')
    g.add_argument("--host", default="192.168.1.101")
    g.add_argument("--user", default="admin")
    g.add_argument("--password", required=True)
    
    # Период
    g = p.add_argument_group('Период')
    g.add_argument("--start", default="2000-01-01T00:00:00",
                   help="Начало (ISO8601 или YYYY-MM-DD)")
    g.add_argument("--end", required=True,
                   help="Конец (ISO8601 или YYYY-MM-DD)")
    g.add_argument("--chunk-days", type=int, default=0,
                   help="Разбить на периоды по N дней (0 = без разбиения)")
    
    # Выход
    g = p.add_argument_group('Выходной файл')
    g.add_argument("--out", default="events.ndjson")
    g.add_argument("--force", action="store_true",
                   help="Перезаписать существующий")
    g.add_argument("--append", action="store_true",
                   help="Дополнить существующий")
    g.add_argument("--backup", action="store_true",
                   help="Создать резервную копию")
    
    # Дедупликация
    g = p.add_argument_group('Дедупликация')
    g.add_argument("--deduplicate", action="store_true",
                   help="Фильтровать дубликаты")
    g.add_argument("--resume", action="store_true",
                   help="Продолжить с последнего serialNo")
    
    # Запрос
    g = p.add_argument_group('Параметры запроса')
    g.add_argument("--page", type=int, default=30)
    g.add_argument("--major", type=int, default=5)
    g.add_argument("--minor", type=int, default=0)
    g.add_argument("--begin-serial", type=int, default=1)
    g.add_argument("--end-serial", type=int, default=3000000000)
    
    # Изображения
    g = p.add_argument_group('Изображения')
    g.add_argument("--pic", action="store_true")
    g.add_argument("--img-dir", default="event_images")
    g.add_argument("--no-save-images", action="store_true")
    
    # Сеть
    g = p.add_argument_group('Сеть')
    g.add_argument("--timeout", type=int, default=180)
    g.add_argument("--retries", type=int, default=5)
    g.add_argument("--sleep", type=float, default=0.0)
    
    # Отладка
    g.add_argument("--verbose", "-v", action="store_true")
    
    return p


def main() -> None:
    """Точка входа"""
    args = create_parser().parse_args()
    
    # Валидация
    if args.append and args.force:
        print("⚠️  --append и --force несовместимы, используем --append")
        args.force = False
    
    exporter = EventExporter(args)
    start = time.perf_counter()
    
    try:
        exporter.run()
    except KeyboardInterrupt:
        print(f"\n\n⚠️ Прервано. Экспортировано: {exporter.total_exported}")
    finally:
        elapsed = time.perf_counter() - start
        print(f"\n⏱️  Время: {elapsed:.1f}с")


if __name__ == "__main__":
    main()
