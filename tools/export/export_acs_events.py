#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Export Hikvision/HiWatch AccessControl events via ISAPI:
  POST /ISAPI/AccessControl/AcsEvent?format=json

Designed for face/access terminals that:
  - require "minor" parameter
  - cap maxResults to 30
  - may return multipart/mixed (JSON + JPEG) when picEnable=true

Output:
  - NDJSON file: one event per line (dict)
  - Optional: save JPEG parts (if multipart) to --img-dir

Dependencies:
  pip install requests requests-toolbelt
"""

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple
from functools import wraps

import requests
from requests.auth import HTTPDigestAuth
from requests.exceptions import ConnectionError, ReadTimeout

try:
    from requests_toolbelt.multipart.decoder import MultipartDecoder
except Exception:  # pragma: no cover
    MultipartDecoder = None  # type: ignore


# === ПРОФИЛИРОВАНИЕ ВРЕМЕНИ ===
_timing_stats = {}


def timeit(func):
    """Декоратор для замера времени выполнения функции"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        func_name = func.__name__
        start = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            elapsed = time.perf_counter() - start
            if func_name not in _timing_stats:
                _timing_stats[func_name] = {'calls': 0, 'total': 0.0, 'min': float('inf'), 'max': 0.0}
            
            stats = _timing_stats[func_name]
            stats['calls'] += 1
            stats['total'] += elapsed
            stats['min'] = min(stats['min'], elapsed)
            stats['max'] = max(stats['max'], elapsed)
    
    return wrapper


def print_timing_stats():
    """Вывод статистики времени выполнения"""
    if not _timing_stats:
        return
    
    print("\n" + "=" * 80)
    print("⏱️  СТАТИСТИКА ВРЕМЕНИ ВЫПОЛНЕНИЯ")
    print("=" * 80)
    print(f"{'Функция':<30} {'Вызовов':<10} {'Всего (сек)':<15} {'Среднее':<12} {'Мин':<10} {'Макс':<10}")
    print("-" * 80)
    
    for func_name, stats in sorted(_timing_stats.items(), key=lambda x: x[1]['total'], reverse=True):
        avg = stats['total'] / stats['calls'] if stats['calls'] > 0 else 0
        print(f"{func_name:<30} {stats['calls']:<10} {stats['total']:<15.3f} {avg:<12.3f} {stats['min']:<10.3f} {stats['max']:<10.3f}")
    
    total_time = sum(s['total'] for s in _timing_stats.values())
    print("-" * 80)
    print(f"{'ИТОГО':<30} {'':<10} {total_time:<15.3f}")
    print("=" * 80)
# === КОНЕЦ ПРОФИЛИРОВАНИЯ ===


@timeit
def extract_events(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return AcsEvent.InfoList (list of event dicts)."""
    acs = payload.get("AcsEvent")
    if isinstance(acs, dict):
        info = acs.get("InfoList")
        if isinstance(info, list):
            return [x for x in info if isinstance(x, dict)]
    return []


@timeit
def is_device_error(payload: Dict[str, Any]) -> bool:
    """Hikvision-style JSON_ResponseStatus usually contains statusCode/statusString."""
    return isinstance(payload, dict) and "statusCode" in payload and "statusString" in payload


def ensure_dir(path: str) -> None:
    if path:
        os.makedirs(path, exist_ok=True)


@timeit
def parse_json_or_multipart(
    resp: requests.Response,
    save_images: bool,
    img_dir: Optional[str],
    img_prefix: str,
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Returns (payload_json, saved_image_paths).
    If Content-Type is multipart/mixed, extract JSON part and optionally save JPEG parts.
    """
    ct = (resp.headers.get("Content-Type") or "").lower()
    saved: List[str] = []

    if "multipart" in ct:
        if MultipartDecoder is None:
            raise RuntimeError(
                "Device returned multipart response but requests-toolbelt is not installed. "
                "Install: pip install requests-toolbelt"
            )

        dec = MultipartDecoder(resp.content, resp.headers.get("Content-Type", ""))

        json_part = None
        for part in dec.parts:
            pct = part.headers.get(b"Content-Type", b"").decode(errors="ignore").lower()
            if "application/json" in pct:
                json_part = part
                break

        if json_part is None:
            # some devices put JSON without explicit application/json; fallback to first part as text
            first = dec.parts[0].content.decode("utf-8", "ignore") if dec.parts else ""
            raise RuntimeError(f"Multipart response without JSON part. First part: {first[:300]}")

        payload = json.loads(json_part.content.decode("utf-8", "ignore"))

        if save_images and img_dir:
            ensure_dir(img_dir)
            idx = 0
            for part in dec.parts:
                pct = part.headers.get(b"Content-Type", b"").decode(errors="ignore").lower()
                if "image/jpeg" in pct or "image/jpg" in pct:
                    fname = f"{img_prefix}_img{idx}.jpg"
                    fpath = os.path.join(img_dir, fname)
                    with open(fpath, "wb") as f:
                        f.write(part.content)
                    saved.append(fpath)
                    idx += 1

        return payload, saved

    # non-multipart: expect JSON
    # some devices may still return XML on error (e.g., <userCheck/>)
    if "json" not in ct:
        body = resp.text[:500]
        raise RuntimeError(f"Non-JSON response (Content-Type={ct}). Body: {body}")

    return resp.json(), saved


@timeit
def post_acs_event(
    session: requests.Session,
    base_url: str,
    auth: HTTPDigestAuth,
    cond: Dict[str, Any],
    timeout_s: int,
    retries: int,
    backoff_s: float,
    save_images: bool,
    img_dir: Optional[str],
    img_prefix: str,
) -> Tuple[Dict[str, Any], List[str], requests.Session]:
    """
    POST AcsEvent with retries. Returns (payload_json, saved_image_paths, session).
    Important: we return session because we may recreate it on failures.
    """
    url = f"{base_url}/ISAPI/AccessControl/AcsEvent?format=json"
    timeout = (5, timeout_s)  # (connect, read)

    last_err: Optional[Exception] = None

    for attempt in range(1, retries + 1):
        try:
            resp = session.post(url, auth=auth, json={"AcsEventCond": cond}, timeout=timeout)

            if resp.status_code == 401:
                raise RuntimeError(f"Unauthorized (401). Body: {resp.text[:200]}")
            if resp.status_code >= 400:
                raise RuntimeError(f"HTTP {resp.status_code}. Body: {resp.text[:300]}")

            payload, saved = parse_json_or_multipart(
                resp, save_images=save_images, img_dir=img_dir, img_prefix=img_prefix
            )

            if is_device_error(payload):
                raise RuntimeError(f"Device error: {payload}")

            return payload, saved, session

        except (ReadTimeout, ConnectionError) as e:
            last_err = e
            time.sleep(backoff_s * attempt)

            # recreate session (return it to caller!)
            try:
                session.close()
            except Exception:
                pass

            session = requests.Session()
            session.headers.update({"Accept": "application/json", "Connection": "close"})
            continue

        except Exception as e:
            # For non-transient problems (badJsonContent, bad parameters, etc.) don't spam retries.
            raise

    raise RuntimeError(f"Failed after {retries} retries. Last error: {last_err!r}")


def main() -> None:
    p = argparse.ArgumentParser(description="Export ACT-T1342EW access events (ISAPI AcsEvent) to NDJSON.")
    p.add_argument("--host", default="192.168.1.101")
    p.add_argument("--user", default="admin")
    p.add_argument("--password", required=True)

    p.add_argument("--out", default="events.ndjson")
    p.add_argument("--verbose", action="store_true", help="Подробный вывод времени каждого запроса")

    # For your device: local format without timezone in request is accepted,
    # while response may include +03:00.
    p.add_argument("--start", default="2000-01-01T00:00:00")
    p.add_argument("--end", required=True, help="ISO8601 local, e.g. 2025-12-15T23:59:59")

    p.add_argument("--page", type=int, default=30, help="maxResults (device max often 30)")
    p.add_argument("--timeout", type=int, default=180, help="read timeout seconds")
    p.add_argument("--sleep", type=float, default=0.0)

    # On your firmware minor is required; use 0 for 'all minors within major'
    p.add_argument("--major", type=int, default=5)
    p.add_argument("--minor", type=int, default=0)

    # Export mode: serial-based paging (recommended)
    p.add_argument("--begin-serial", type=int, default=1)
    p.add_argument("--end-serial", type=int, default=3000000000)

    # Pictures:
    p.add_argument("--pic", action="store_true", help="Enable picEnable=true and parse multipart response")
    p.add_argument("--img-dir", default="event_images", help="Directory to save JPEG parts when --pic")
    p.add_argument("--no-save-images", action="store_true", help="If set with --pic, parse JSON but do not save JPEGs")

    # Retry behavior:
    p.add_argument("--retries", type=int, default=5)
    p.add_argument("--backoff", type=float, default=1.0)

    args = p.parse_args()

    base_url = f"http://{args.host}"
    auth = HTTPDigestAuth(args.user, args.password)

    session = requests.Session()
    session.headers.update({"Accept": "application/json", "Connection": "close"})

    next_serial = int(args.begin_serial)
    total = 0

    # if --pic but user doesn't want files
    save_images = bool(args.pic) and not bool(args.no_save_images)
    img_dir = args.img_dir if save_images else None

    # Clear output file
    with open(args.out, "w", encoding="utf-8") as f:
        iteration = 0
        while True:
            iteration += 1
            iteration_start = time.perf_counter()
            
            cond: Dict[str, Any] = {
                "searchID": "export-all-serial",
                "searchResultPosition": 0,
                "maxResults": int(args.page),
                "major": int(args.major),
                "minor": int(args.minor),
                "startTime": args.start,
                "endTime": args.end,
                "picEnable": bool(args.pic),
                "timeReverseOrder": False,
                "beginSerialNo": next_serial,
                "endSerialNo": int(args.end_serial),
            }

            img_prefix = f"serial_{next_serial}"

            request_start = time.perf_counter()
            payload, saved_imgs, session = post_acs_event(
                session=session,
                base_url=base_url,
                auth=auth,
                cond=cond,
                timeout_s=int(args.timeout),
                retries=int(args.retries),
                backoff_s=float(args.backoff),
                save_images=save_images,
                img_dir=img_dir,
                img_prefix=img_prefix,
            )
            request_elapsed = time.perf_counter() - request_start

            events = extract_events(payload)
            if not events:
                break

            max_sn: Optional[int] = None
            for e in events:
                # attach saved images list only to the first event of this batch (optional),
                # or you can attach to each event if you prefer.
                if saved_imgs:
                    e = dict(e)  # shallow copy
                    e["_savedImages"] = saved_imgs

                f.write(json.dumps(e, ensure_ascii=False) + "\n")
                total += 1

                sn = e.get("serialNo")
                if isinstance(sn, int):
                    max_sn = sn if max_sn is None else max(max_sn, sn)

            if max_sn is None:
                raise RuntimeError("No serialNo in returned events; cannot continue serial paging.")

            next_serial = max_sn + 1
            
            iteration_elapsed = time.perf_counter() - iteration_start

            if args.verbose:
                sys.stderr.write(f"\rИтерация {iteration}: запрос={request_elapsed:.2f}с, итого={iteration_elapsed:.2f}с, событий={len(events)}, всего={total}")
            else:
                sys.stderr.write(f"\rExported: {total}  (next_serial={next_serial})")
            sys.stderr.flush()

            if len(events) < int(args.page):
                break

            if args.sleep > 0:
                time.sleep(float(args.sleep))

    sys.stderr.write("\n")
    print(f"OK: wrote {total} events to {args.out}")
    if args.pic:
        print("Note: --pic enabled. If device returns multipart, JSON is extracted; JPEG parts saved if not --no-save-images.")
    
    # Вывод статистики времени
    print_timing_stats()


if __name__ == "__main__":
    script_start = time.perf_counter()
    try:
        main()
    finally:
        script_elapsed = time.perf_counter() - script_start
        print(f"\n⏱️  Общее время выполнения скрипта: {script_elapsed:.2f} секунд")
