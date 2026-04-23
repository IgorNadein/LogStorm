#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Backfill helpers for collector images."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Optional, TYPE_CHECKING

import requests
from requests.auth import HTTPDigestAuth

try:
    from .isapi import (
        build_request_conditions,
        parse_multipart_response,
        process_event_images,
    )
except ImportError:  # pragma: no cover - direct script execution
    from isapi import (
        build_request_conditions,
        parse_multipart_response,
        process_event_images,
    )

if TYPE_CHECKING:  # pragma: no cover
    from .storage import EventStorage


def build_backfill_request_conditions(
    event: dict[str, Any],
    config: dict[str, Any],
    window_minutes: int = 5,
) -> dict[str, Any]:
    """Build historical single-event backfill request."""
    serial = event.get("serialNo")
    event_time = event.get("time")
    if serial is None or not event_time:
        raise ValueError("Событие должно содержать serialNo и time")

    dt = datetime.fromisoformat(str(event_time).replace("Z", "+00:00"))
    start_time = (dt - timedelta(minutes=window_minutes)).strftime(
        "%Y-%m-%dT%H:%M:%S"
    )
    end_time = (dt + timedelta(minutes=window_minutes)).strftime(
        "%Y-%m-%dT%H:%M:%S"
    )
    req = config.get("request", {})
    return {
        "searchID": "collector-photo-backfill",
        "searchResultPosition": 0,
        "maxResults": max(1, min(req.get("page_size", 30), 16)),
        "major": req.get("major", 5),
        "minor": req.get("minor", 0),
        "startTime": start_time,
        "endTime": end_time,
        "picEnable": True,
        "timeReverseOrder": False,
        "beginSerialNo": int(serial),
        "endSerialNo": int(serial),
    }


def get_event_identity(event: dict[str, Any]) -> tuple[Optional[str], Optional[int]]:
    """Extract event id and serialNo for matching."""
    event_id = None
    for key in ("eventID", "eventId", "event_id"):
        value = event.get(key)
        if value not in (None, ""):
            event_id = str(value)
            break

    serial = event.get("serialNo")
    serial_no = int(serial) if serial is not None else None
    return event_id, serial_no


def remove_pending_event(
    pending_by_serial: dict[int, dict[str, Any]],
    pending_by_event_id: dict[str, dict[str, Any]],
    event: dict[str, Any],
) -> None:
    """Remove event from pending backfill maps."""
    event_id, serial_no = get_event_identity(event)
    if event_id is not None:
        pending_by_event_id.pop(event_id, None)
    if serial_no is not None:
        pending_by_serial.pop(serial_no, None)


def pop_matching_pending_event(
    candidate_event: dict[str, Any],
    pending_by_serial: dict[int, dict[str, Any]],
    pending_by_event_id: dict[str, dict[str, Any]],
) -> Optional[dict[str, Any]]:
    """Pop matching pending event by event id or serialNo."""
    event_id, serial_no = get_event_identity(candidate_event)

    if event_id is not None and event_id in pending_by_event_id:
        event = pending_by_event_id[event_id]
        remove_pending_event(pending_by_serial, pending_by_event_id, event)
        return event

    if serial_no is not None and serial_no in pending_by_serial:
        event = pending_by_serial[serial_no]
        remove_pending_event(pending_by_serial, pending_by_event_id, event)
        return event

    return None


def backfill_event_image(
    device: dict[str, Any],
    event: dict[str, Any],
    config: dict[str, Any],
    logger: logging.Logger,
    *,
    requests_module=requests,
    build_backfill_request_conditions_fn=build_backfill_request_conditions,
    parse_multipart_response_fn=parse_multipart_response,
    process_event_images_fn=process_event_images,
) -> Optional[dict[str, Any]]:
    """Backwards-compatible single-event image backfill helper."""
    host = device["host"]
    device_name = device.get("name", host)
    user = device["user"]
    password = device["password"]
    req = config.get("request", {})
    images_cfg = config.get("images", {})

    serial = event.get("serialNo")
    if serial is None or event.get("_imagePath"):
        return None

    base_url = f"http://{host}"
    auth = HTTPDigestAuth(user, password)
    session = requests_module.Session()
    session.headers.update({"Accept": "application/json"})

    try:
        cond = build_backfill_request_conditions_fn(event, config)
        url = f"{base_url}/ISAPI/AccessControl/AcsEvent?format=json"
        resp = session.post(
            url,
            auth=auth,
            json={"AcsEventCond": cond},
            timeout=(5, req.get("timeout", 180)),
        )

        if resp.status_code >= 400:
            logger.warning(
                f"    [{device_name}][WARN] Backfill HTTP {resp.status_code} "
                f"for serial {serial}"
            )
            return None

        ct = (resp.headers.get("Content-Type") or "").lower()
        if "multipart" in ct:
            payload, images_data = parse_multipart_response_fn(
                resp,
                True,
                logger,
                device_name,
            )
            if payload is None:
                return None
        else:
            payload = resp.json()
            images_data = {}

        if "statusCode" in payload:
            logger.warning(
                f"    [{device_name}][WARN] Backfill rejected by device for "
                f"serial {serial}: {payload.get('statusString', 'unknown')}"
            )
            return None

        fetched_events = payload.get("AcsEvent", {}).get("InfoList", [])
        matched_event = None
        expected_event_id, expected_serial = get_event_identity(event)
        for candidate in fetched_events:
            candidate_event_id, candidate_serial = get_event_identity(candidate)
            if (
                expected_event_id is not None
                and candidate_event_id is not None
                and candidate_event_id == expected_event_id
            ):
                matched_event = candidate
                break
            if expected_serial is not None and candidate_serial == expected_serial:
                matched_event = candidate
                break

        if matched_event is None:
            return None

        process_event_images_fn(
            [matched_event],
            images_data,
            images_cfg,
            auth,
            session,
            logger,
        )
        if not matched_event.get("_imagePath"):
            return None

        updated_event = dict(event)
        updated_event.update(matched_event)
        updated_event["_device"] = event.get("_device", host)
        updated_event["_device_name"] = event.get("_device_name", device_name)
        updated_event["_collected"] = event.get("_collected", "")
        return updated_event
    except Exception as exc:
        logger.warning(
            f"    [{device_name}][WARN] Не удалось догрузить фото для serial "
            f"{serial}: {type(exc).__name__}: {exc}"
        )
        return None
    finally:
        session.close()


def backfill_device_images(
    device: dict[str, Any],
    pending_events: list[dict[str, Any]],
    storage: "EventStorage",
    config: dict[str, Any],
    logger: logging.Logger,
    *,
    requests_module=requests,
    build_request_conditions_fn=build_request_conditions,
    parse_multipart_response_fn=parse_multipart_response,
    process_event_images_fn=process_event_images,
) -> tuple[int, int]:
    """Backfill images for one device via paged event scan."""
    host = device["host"]
    device_name = device.get("name", host)
    user = device["user"]
    password = device["password"]
    req = config.get("request", {})
    images_cfg = config.get("images", {})
    if not pending_events:
        return 0, 0

    pending_sorted = sorted(
        (
            event
            for event in pending_events
            if event.get("serialNo") is not None and not event.get("_imagePath")
        ),
        key=lambda event: (
            int(event.get("serialNo", 0)),
            str(event.get("time", "")),
        ),
    )
    if not pending_sorted:
        return 0, 0

    pending_by_serial: dict[int, dict[str, Any]] = {}
    pending_by_event_id: dict[str, dict[str, Any]] = {}
    for event in pending_sorted:
        event_id, serial_no = get_event_identity(event)
        if serial_no is None:
            continue
        pending_by_serial[serial_no] = event
        if event_id is not None:
            pending_by_event_id[event_id] = event

    if not pending_by_serial:
        return 0, 0

    serials = sorted(pending_by_serial.keys())
    start_serial = serials[0]
    max_pending_serial = serials[-1]

    event_times = [
        datetime.fromisoformat(str(event["time"]).replace("Z", "+00:00"))
        for event in pending_sorted
        if event.get("time")
    ]
    if event_times:
        start_time = (min(event_times) - timedelta(hours=1)).strftime(
            "%Y-%m-%dT%H:%M:%S"
        )
        end_time = max(event_times).strftime("%Y-%m-%dT%H:%M:%S")
    else:
        now = datetime.now()
        start_time = (now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S")
        end_time = now.strftime("%Y-%m-%dT%H:%M:%S")

    base_url = f"http://{host}"
    auth = HTTPDigestAuth(user, password)
    session = requests_module.Session()
    session.headers.update({"Accept": "application/json"})

    next_serial = start_serial
    updated_count = 0
    skipped_count = 0

    try:
        url = f"{base_url}/ISAPI/AccessControl/AcsEvent?format=json"
        iteration = 0

        while pending_by_serial:
            iteration += 1
            cond = build_request_conditions_fn(
                start_time,
                end_time,
                next_serial,
                config,
                save_images=True,
            )
            resp = session.post(
                url,
                auth=auth,
                json={"AcsEventCond": cond},
                timeout=(5, req.get("timeout", 180)),
            )

            logger.debug(
                f"    [{device_name}][backfill {iteration}] serial "
                f"from {next_serial}, pending {len(pending_by_serial)}"
            )

            if resp.status_code >= 400:
                logger.warning(
                    f"    [{device_name}][WARN] Backfill HTTP "
                    f"{resp.status_code} from serial {next_serial}"
                )
                break

            ct = (resp.headers.get("Content-Type") or "").lower()
            if "multipart" in ct:
                payload, images_data = parse_multipart_response_fn(
                    resp,
                    True,
                    logger,
                    device_name,
                )
                if payload is None:
                    break
            else:
                payload = resp.json()
                images_data = {}

            if "statusCode" in payload:
                logger.warning(
                    f"    [{device_name}][WARN] Backfill rejected by device: "
                    f"{payload.get('statusString', 'unknown')}"
                )
                break

            fetched_events = payload.get("AcsEvent", {}).get("InfoList", [])
            if not fetched_events:
                break

            matched_pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
            for candidate in fetched_events:
                pending_event = pop_matching_pending_event(
                    candidate,
                    pending_by_serial,
                    pending_by_event_id,
                )
                if pending_event is not None:
                    matched_pairs.append((pending_event, candidate))

            if matched_pairs:
                matched_candidates = [candidate for _, candidate in matched_pairs]
                process_event_images_fn(
                    matched_candidates,
                    images_data,
                    images_cfg,
                    auth,
                    session,
                    logger,
                )

                for pending_event, candidate in matched_pairs:
                    image_path = candidate.get("_imagePath")
                    if not image_path:
                        skipped_count += 1
                        continue

                    serial = pending_event.get("serialNo")
                    if serial is None:
                        skipped_count += 1
                        continue

                    updated = storage.update_event_image(
                        host,
                        int(serial),
                        image_path,
                    )
                    if updated:
                        updated_count += 1
                        logger.info(
                            f"    [OK] {device_name}: serial {serial} -> "
                            "фото сохранено"
                        )
                    else:
                        skipped_count += 1

            max_sn = max(
                (int(event.get("serialNo", 0)) for event in fetched_events),
                default=0,
            )
            if max_sn <= 0:
                break

            next_serial = max_sn + 1
            if next_serial > max_pending_serial:
                break
    except Exception as exc:
        logger.warning(
            f"    [{device_name}][WARN] Не удалось выполнить backfill: "
            f"{type(exc).__name__}: {exc}"
        )
    finally:
        session.close()

    return updated_count, skipped_count + len(pending_by_serial)
