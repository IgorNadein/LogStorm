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
  python collector.py --config collector.local.py

  # Создать пример конфигурации
  python collector.py --init
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from threading import Event, Lock
from typing import Any, Dict, List, Optional

import requests

try:
    from .backfill import (
        backfill_device_images as _backfill_device_images,
        backfill_event_image as _backfill_event_image,
        build_backfill_request_conditions as _build_backfill_request_conditions,
        get_event_identity as _get_event_identity,
        pop_matching_pending_event as _pop_matching_pending_event,
        remove_pending_event as _remove_pending_event,
    )
    from .config import (
        DEFAULT_CONFIG,
        get_app_dir,
        is_db_url,
        load_config,
        load_python_config,
        save_default_config,
    )
    from .isapi import (
        FetchResult,
        build_request_conditions as _build_request_conditions,
        download_image as _download_image,
        fetch_events_from_device as _fetch_events_from_device,
        parse_multipart_response as _parse_multipart_response,
        process_event_images as _process_event_images,
        save_image as _save_image,
    )
    from .log_setup import setup_logging
    from .storage import EventStorage
    from .tracker import EventTracker
except ImportError:  # pragma: no cover - direct script execution
    from backfill import (
        backfill_device_images as _backfill_device_images,
        backfill_event_image as _backfill_event_image,
        build_backfill_request_conditions as _build_backfill_request_conditions,
        get_event_identity as _get_event_identity,
        pop_matching_pending_event as _pop_matching_pending_event,
        remove_pending_event as _remove_pending_event,
    )
    from config import (
        DEFAULT_CONFIG,
        get_app_dir,
        is_db_url,
        load_config,
        load_python_config,
        save_default_config,
    )
    from isapi import (
        FetchResult,
        build_request_conditions as _build_request_conditions,
        download_image as _download_image,
        fetch_events_from_device as _fetch_events_from_device,
        parse_multipart_response as _parse_multipart_response,
        process_event_images as _process_event_images,
        save_image as _save_image,
    )
    from log_setup import setup_logging
    from storage import EventStorage
    from tracker import EventTracker


save_image = _save_image
download_image = _download_image
build_request_conditions = _build_request_conditions
build_backfill_request_conditions = _build_backfill_request_conditions
get_event_identity = _get_event_identity
remove_pending_event = _remove_pending_event
pop_matching_pending_event = _pop_matching_pending_event


def parse_multipart_response(
    resp: requests.Response,
    save_images: bool,
    logger: logging.Logger,
    device_name: str,
):
    """Facade wrapper kept for backwards-compatible monkeypatch targets."""
    return _parse_multipart_response(resp, save_images, logger, device_name)


def process_event_images(
    events: List[Dict[str, Any]],
    images_data: Dict[str, bytes],
    images_cfg: Dict[str, Any],
    auth,
    session: requests.Session,
    logger: logging.Logger,
) -> int:
    """Facade wrapper kept for backwards-compatible monkeypatch targets."""
    return _process_event_images(
        events,
        images_data,
        images_cfg,
        auth,
        session,
        logger,
    )


def fetch_events_from_device(
    device: Dict[str, Any],
    start_time: str,
    end_time: str,
    config: Dict[str, Any],
    logger: logging.Logger,
    start_serial: int = 1,
) -> FetchResult:
    """Facade wrapper for device collection with patch-friendly dependencies."""
    return _fetch_events_from_device(
        device,
        start_time,
        end_time,
        config,
        logger,
        start_serial=start_serial,
        requests_module=requests,
        parse_multipart_response_fn=parse_multipart_response,
        process_event_images_fn=process_event_images,
    )


def backfill_event_image(
    device: Dict[str, Any],
    event: Dict[str, Any],
    config: Dict[str, Any],
    logger: logging.Logger,
) -> Optional[Dict[str, Any]]:
    """Facade wrapper for single-event backfill with patch-friendly hooks."""
    return _backfill_event_image(
        device,
        event,
        config,
        logger,
        requests_module=requests,
        build_backfill_request_conditions_fn=build_backfill_request_conditions,
        parse_multipart_response_fn=parse_multipart_response,
        process_event_images_fn=process_event_images,
    )


def backfill_device_images(
    device: Dict[str, Any],
    pending_events: List[Dict[str, Any]],
    storage: EventStorage,
    config: Dict[str, Any],
    logger: logging.Logger,
) -> tuple[int, int]:
    """Facade wrapper for batch backfill with patch-friendly hooks."""
    return _backfill_device_images(
        device,
        pending_events,
        storage,
        config,
        logger,
        requests_module=requests,
        build_request_conditions_fn=build_request_conditions,
        parse_multipart_response_fn=parse_multipart_response,
        process_event_images_fn=process_event_images,
    )


class Collector:
    """Основной класс сборщика событий СКУД."""

    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        self.config = config
        self.logger = logger
        initial_days = config.get("initial_days", 30)

        storage_config = config.get("storage", {})
        ndjson_file = storage_config.get("ndjson") or config.get("output_file")
        if not ndjson_file:
            raise ValueError(
                "Не указан путь к NDJSON файлу. "
                "Используйте storage.ndjson или output_file"
            )
        if not os.path.isabs(ndjson_file):
            ndjson_file = os.path.join(get_app_dir(), ndjson_file)

        sqlite_file = storage_config.get("sqlite") or config.get("sqlite_file")
        if sqlite_file and not is_db_url(sqlite_file) and not os.path.isabs(sqlite_file):
            sqlite_file = os.path.join(get_app_dir(), sqlite_file)

        self.ndjson_file = ndjson_file
        self.sqlite_file = sqlite_file
        self.storage = EventStorage(ndjson_file, sqlite_file)
        self.tracker = EventTracker(self.storage, initial_days)

        self.stop_event = Event()
        self._file_lock = Lock()

    def _collect_from_device(
        self,
        device: Dict[str, Any],
        end_time: str,
    ) -> Dict[str, Any]:
        """Сбор с одного устройства для параллельного запуска."""
        host = device["host"]
        name = device.get("name", host)

        result_info = {
            "host": host,
            "name": name,
            "new": 0,
            "dup": 0,
            "completed": False,
            "error": None,
        }

        try:
            start_time = self.tracker.get_start_time(host)
            start_serial = self.tracker.get_last_serial(host)

            self.logger.info(f"  📹 {name} ({host})")

            result = fetch_events_from_device(
                device,
                start_time,
                end_time,
                self.config,
                self.logger,
                start_serial=start_serial,
            )

            result_info["events"] = result.events
            result_info["last_serial"] = result.last_serial
            result_info["completed"] = result.completed
            result_info["last_event_time"] = result.last_event_time
        except Exception as exc:
            result_info["error"] = str(exc)
            self.logger.error(f"    [ERROR] {name}: {exc}")

        return result_info

    def _collect_results(
        self,
        active_devices: List[Dict[str, Any]],
        end_time: str,
        max_workers: int,
    ) -> List[Dict[str, Any]]:
        """Run device collection in parallel and return per-device results."""
        results: List[Dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self._collect_from_device, device, end_time): device
                for device in active_devices
            }
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as exc:
                    device = futures[future]
                    self.logger.error(f"    [ERROR] {device['host']}: {exc}")
        return results

    def _process_result(
        self,
        result_info: Dict[str, Any],
        end_time: str,
    ) -> tuple[int, int]:
        """Filter duplicates, persist events and update device state."""
        host = result_info["host"]
        name = result_info["name"]
        last_serial_state = self.tracker.get_last_serial(host)
        new_count = 0
        dup_count = 0
        events_to_write: List[Dict[str, Any]] = []

        for event in result_info["events"]:
            serial = event.get("serialNo")
            if serial is None:
                dup_count += 1
                continue
            if int(serial) <= int(last_serial_state):
                dup_count += 1
                continue
            if self.tracker.is_duplicate(host, int(serial)):
                dup_count += 1
                continue

            event["_device"] = host
            event["_device_name"] = name
            event["_collected"] = datetime.now().isoformat()
            events_to_write.append(event)
            new_count += 1

        if events_to_write:
            self.storage.write_events(events_to_write)

        last_serial = result_info.get("last_serial", 0)
        if last_serial > 0:
            self.tracker.update_last_serial(host, last_serial)

        if result_info["completed"]:
            update_time = result_info.get("last_event_time") or end_time
            self.tracker.update_last_collect(host, update_time)
            status = "✅"
        else:
            status = "⚠️"

        self.logger.info(
            f"    [{status}] {name}: {new_count} новых, {dup_count} дубликатов"
        )
        return new_count, dup_count

    def collect_once(self) -> int:
        """Однократный сбор со всех устройств."""
        output_file = self.ndjson_file
        devices = self.config.get("devices", [])
        max_workers = self.config.get("max_parallel", 4)

        active_devices = [device for device in devices if device.get("enabled", True)]
        self.logger.info(f"🔄 Начало сбора ({len(active_devices)} устройств)")

        end_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        output_dir = os.path.dirname(output_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        results = self._collect_results(active_devices, end_time, max_workers)

        total_new = 0
        total_dup = 0
        for result_info in results:
            if result_info.get("error") or "events" not in result_info:
                continue
            new_count, dup_count = self._process_result(result_info, end_time)
            total_new += new_count
            total_dup += dup_count

        self.logger.info(f"📊 Итого: {total_new} новых, {total_dup} дубликатов")
        return total_new

    def run_loop(self) -> None:
        """Запуск в режиме демона."""
        interval = self.config.get("interval_minutes", 15) * 60
        self.logger.info(f"🚀 Запуск сборщика (интервал: {interval // 60} мин)")

        while not self.stop_event.is_set():
            try:
                self.collect_once()
            except Exception as exc:
                self.logger.error(f"[ERROR] Критическая ошибка: {exc}")

            self.logger.info(f"💤 Следующий сбор через {interval // 60} минут")
            self.stop_event.wait(interval)

        self.logger.info("🛑 Сборщик остановлен")

    def backfill_missing_images(self, limit: Optional[int] = None) -> int:
        """
        Догрузить фото для уже собранных событий без `_imagePath`.

        Обновляет только SQLite. NDJSON остаётся неизменяемым журналом.
        """
        devices = self.config.get("devices", [])
        device_map = {
            device["host"]: device
            for device in devices
            if device.get("enabled", True)
        }
        if not device_map:
            self.logger.warning("Нет активных устройств для backfill фотографий")
            return 0

        missing_events = list(
            self.storage.iter_events_without_images(
                limit=limit,
                newest_first=True,
            )
        )
        if not missing_events:
            self.logger.info("Событий без фотографий не найдено")
            return 0

        self.logger.info(
            f"🖼️ Backfill фотографий: проверяю {len(missing_events)} событий"
        )

        missing_by_device: Dict[str, List[Dict[str, Any]]] = {}
        skipped_count = 0
        for event in missing_events:
            host = event.get("_device")
            serial = event.get("serialNo")
            if not host or host not in device_map or serial is None:
                skipped_count += 1
                continue
            missing_by_device.setdefault(host, []).append(event)

        updated_count = 0
        for host, device_events in missing_by_device.items():
            device = device_map[host]
            device_name = device.get("name", host)
            self.logger.info(
                f"  📹 {device_name} ({host}) -> backfill {len(device_events)} "
                "событий без фото"
            )
            updated, remaining = backfill_device_images(
                device,
                device_events,
                self.storage,
                self.config,
                self.logger,
            )
            updated_count += updated
            skipped_count += remaining

        self.logger.info(
            f"📊 Backfill завершён: {updated_count} обновлено, "
            f"{skipped_count} пропущено"
        )
        return updated_count

    def stop(self) -> None:
        """Остановка сборщика."""
        self.stop_event.set()


def main(argv: Optional[List[str]] = None):
    parser = argparse.ArgumentParser(
        description="LogStorm Collector - Сборщик событий СКУД"
    )

    parser.add_argument("--config", "-c", default="collector.local.py", help="Путь к конфигурации")
    parser.add_argument("--once", action="store_true", help="Однократный сбор и выход")
    parser.add_argument("--init", action="store_true", help="Создать пример конфигурации")
    parser.add_argument("--verbose", "-v", action="store_true", help="Подробный вывод")
    parser.add_argument(
        "--backfill-images",
        action="store_true",
        help="Догрузить фото для уже собранных событий",
    )
    parser.add_argument(
        "--backfill-limit",
        type=int,
        default=None,
        help="Ограничить число событий для backfill",
    )

    args = parser.parse_args(argv)

    if args.init:
        save_default_config(args.config)
        return

    config_path = args.config
    if not os.path.isabs(config_path):
        config_path = os.path.join(get_app_dir(), config_path)

    config = load_config(config_path)

    log_file = config.get("log_file", "collector.log")
    if not os.path.isabs(log_file):
        log_file = os.path.join(get_app_dir(), log_file)

    logger = setup_logging(log_file, args.verbose)
    collector = Collector(config, logger)

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

    if args.backfill_images:
        collector.backfill_missing_images(limit=args.backfill_limit)
    elif args.once:
        collector.collect_once()
    else:
        collector.run_loop()


if __name__ == "__main__":
    main()
