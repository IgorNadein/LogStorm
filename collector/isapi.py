#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ISAPI helpers for collector event and image retrieval."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, NamedTuple, Optional

import requests
from requests.auth import HTTPDigestAuth
from requests.exceptions import ConnectionError, ReadTimeout

try:
    from requests_toolbelt.multipart.decoder import MultipartDecoder
except ImportError:  # pragma: no cover - optional dependency
    MultipartDecoder = None


class FetchResult(NamedTuple):
    """Device collection result."""

    events: list[dict[str, Any]]
    last_serial: int
    completed: bool
    last_event_time: Optional[str] = None


def save_image(
    image_data: bytes,
    event: dict[str, Any],
    images_config: dict[str, Any],
    logger: logging.Logger,
) -> Optional[str]:
    """Persist event image and return local path."""
    folder = images_config.get("folder", "images")
    fmt = images_config.get(
        "format",
        "{date}/{employeeNoString}_{serialNo}.jpg",
    )

    serial = event.get("serialNo", 0)
    employee = event.get("employeeNoString", "unknown")
    event_time = event.get("time", "")
    date_str = event_time[:10] if event_time else "unknown"

    filename = fmt.format(
        date=date_str,
        serialNo=serial,
        employeeNoString=employee,
        time=event_time.replace(":", "-") if event_time else "unknown",
    )
    filepath = os.path.join(folder, filename)

    filedir = os.path.dirname(filepath)
    if filedir:
        os.makedirs(filedir, exist_ok=True)

    try:
        with open(filepath, "wb") as handle:
            handle.write(image_data)
        return filepath
    except Exception as exc:
        logger.warning(f"    [WARN] Не удалось сохранить изображение: {exc}")
        return None


def download_image(
    pic_url: str,
    auth: HTTPDigestAuth,
    session: requests.Session,
    logger: logging.Logger,
    timeout: int = 10,
) -> Optional[bytes]:
    """Download image from pictureURL."""
    try:
        resp = session.get(pic_url, auth=auth, timeout=timeout)
        if resp.status_code == 200:
            ct = resp.headers.get("Content-Type", "")
            if "image" in ct:
                return resp.content
            logger.debug(f"    [WARN] pictureURL не изображение: {ct}")
        else:
            logger.debug(f"    [WARN] pictureURL HTTP {resp.status_code}")
    except Exception as exc:
        logger.debug(f"    [WARN] Ошибка скачивания: {exc}")
    return None


def build_request_conditions(
    start_time: str,
    end_time: str,
    next_serial: int,
    config: dict[str, Any],
    save_images: bool,
) -> dict[str, Any]:
    """Build standard serial-based ISAPI search conditions."""
    req = config.get("request", {})
    extended_end_time = (
        datetime.fromisoformat(end_time.replace("T", " ")) + timedelta(days=1)
    ).strftime("%Y-%m-%dT%H:%M:%S")

    return {
        "searchID": "collector",
        "searchResultPosition": 0,
        "maxResults": req.get("page_size", 30),
        "major": req.get("major", 5),
        "minor": req.get("minor", 0),
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
    device_name: str,
) -> tuple[Optional[dict[str, Any]], dict[str, bytes]]:
    """Parse Hikvision multipart response into JSON payload and images map."""
    if MultipartDecoder is None:
        logger.error(
            f"    [{device_name}][ERROR] Нужен requests-toolbelt для multipart"
        )
        return None, {}

    dec = MultipartDecoder(resp.content, resp.headers.get("Content-Type", ""))
    payload = None
    images_data: dict[str, bytes] = {}

    for part in dec.parts:
        pct = part.headers.get(b"Content-Type", b"")
        if b"application/json" in pct:
            payload = json.loads(part.content.decode("utf-8", "ignore"))
        elif b"image/" in pct and save_images:
            cid = part.headers.get(b"Content-ID", b"")
            if isinstance(cid, bytes):
                cid = cid.decode("utf-8", "ignore")
            cid = cid.strip("<>")
            if cid:
                images_data[cid] = part.content

    return payload, images_data


def process_event_images(
    events: list[dict[str, Any]],
    images_data: dict[str, bytes],
    images_cfg: dict[str, Any],
    auth: HTTPDigestAuth,
    session: requests.Session,
    logger: logging.Logger,
) -> int:
    """Resolve images from multipart or pictureURL and persist them."""
    images_saved = 0

    if images_data:
        for event in events:
            pic_url = event.get("pictureURL", "")
            if pic_url and pic_url in images_data:
                img_path = save_image(images_data[pic_url], event, images_cfg, logger)
                if img_path:
                    event["_imagePath"] = img_path
                    images_saved += 1
    else:
        for event in events:
            pic_url = event.get("pictureURL", "")
            if pic_url:
                img_data = download_image(pic_url, auth, session, logger)
                if img_data:
                    img_path = save_image(img_data, event, images_cfg, logger)
                    if img_path:
                        event["_imagePath"] = img_path
                        images_saved += 1

    return images_saved


def fetch_events_from_device(
    device: dict[str, Any],
    start_time: str,
    end_time: str,
    config: dict[str, Any],
    logger: logging.Logger,
    start_serial: int = 1,
    *,
    requests_module=requests,
    parse_multipart_response_fn=parse_multipart_response,
    process_event_images_fn=process_event_images,
) -> FetchResult:
    """Fetch events and optional images from one device."""
    host = device["host"]
    device_name = device.get("name", host)
    user = device["user"]
    password = device["password"]
    req = config.get("request", {})
    images_cfg = config.get("images", {})
    save_images = device.get("save_images", images_cfg.get("enabled", False))

    base_url = f"http://{host}"
    auth = HTTPDigestAuth(user, password)
    session = requests_module.Session()
    session.headers.update({"Accept": "application/json"})

    all_events: list[dict[str, Any]] = []
    last_successful_serial = start_serial
    iteration = 0
    completed = True
    images_saved = 0

    logger.debug(f"    [{device_name}] Период: {start_time} -> {end_time}")
    logger.debug(f"    [{device_name}] Начальный serial: {start_serial}")
    if save_images:
        logger.debug(
            f"    [{device_name}] Сохранение изображений: {images_cfg.get('folder')}"
        )

    next_serial = start_serial
    while True:
        iteration += 1
        cond = build_request_conditions(
            start_time,
            end_time,
            next_serial,
            config,
            save_images,
        )
        url = f"{base_url}/ISAPI/AccessControl/AcsEvent?format=json"
        logger.debug(
            f"    [{device_name}][{iteration}] serial from {next_serial}..."
        )

        try:
            import time as _time

            req_start = _time.perf_counter()
            resp = session.post(
                url,
                auth=auth,
                json={"AcsEventCond": cond},
                timeout=(5, req.get("timeout", 180)),
            )

            req_elapsed = _time.perf_counter() - req_start
            status = resp.status_code
            logger.debug(
                f"    [{device_name}][{iteration}] {req_elapsed:.1f}с, HTTP {status}"
            )

            if status == 401:
                logger.error(f"    [{device_name}][ERROR] Авторизация (401)")
                completed = False
                break
            if status >= 400:
                logger.error(f"    [{device_name}][ERROR] HTTP {status}")
                completed = False
                break

            ct = (resp.headers.get("Content-Type") or "").lower()
            if "multipart" in ct:
                payload, images_data = parse_multipart_response_fn(
                    resp,
                    save_images,
                    logger,
                    device_name,
                )
                if payload is None:
                    logger.error(f"    [{device_name}][ERROR] Multipart без JSON")
                    completed = False
                    break
            else:
                payload = resp.json()
                images_data = {}

            if "statusCode" in payload:
                msg = payload.get("statusString", "unknown")
                logger.error(f"    [{device_name}][ERROR] Устройство: {msg}")
                completed = False
                break

            acs = payload.get("AcsEvent", {})
            events = acs.get("InfoList", [])
            logger.debug(f"    [{device_name}][{iteration}] +{len(events)} событий")

            if not events:
                break

            if save_images:
                saved = process_event_images_fn(
                    events,
                    images_data,
                    images_cfg,
                    auth,
                    session,
                    logger,
                )
                images_saved += saved

            all_events.extend(events)

            max_sn = max((event.get("serialNo", 0) for event in events), default=0)
            if max_sn > 0:
                last_successful_serial = max_sn
                next_serial = max_sn + 1

            logger.debug(
                f"    [{device_name}][{iteration}] Всего: {len(all_events)}, "
                f"next_serial: {next_serial}"
            )
        except (ReadTimeout, ConnectionError) as exc:
            error_type = (
                "Таймаут" if isinstance(exc, ReadTimeout) else "Ошибка соединения"
            )
            logger.warning(f"    [{device_name}][WARN] {error_type}: {exc}")
            completed = False
            break
        except Exception as exc:
            logger.error(f"    [{device_name}][ERROR] {type(exc).__name__}: {exc}")
            completed = False
            break

    session.close()

    last_event_time = None
    if all_events:
        last_event_time = all_events[-1].get("time")

    if save_images and images_saved > 0:
        logger.debug(f"    [{device_name}] Сохранено изображений: {images_saved}")

    logger.debug(
        f"    [{device_name}] Итого: {len(all_events)} событий, "
        f"serial: {start_serial} -> {last_successful_serial}"
    )
    return FetchResult(
        all_events,
        last_successful_serial,
        completed,
        last_event_time,
    )
