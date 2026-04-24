#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FastAPI application for LogStorm attendance analysis."""

import base64
import json
import mimetypes
from datetime import date
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import FileResponse

from core import LogStormCore
from core.repositories import attendance_override_to_dict
from analyzer import AttendanceAnalysisRequest, EusrrAttendanceService
from analyzer.logscam_loader import LogsCamLoader
from api.auth import require_token
from api.schemas import (
    AttendanceDayEvent,
    AttendanceAnalyzePayload,
    AttendanceManualOverridePayload,
)
from utils.event_mapper import EventMapper


ISSUE_MARKERS = {
    "is_late": ("late", "опозд"),
    "is_early_leave": ("early", "ранн"),
    "is_underwork": ("underwork", "недоработ"),
    "is_absent": ("absence", "absent", "отсутств"),
}


def create_app(
    db_path: Optional[str] = None,
    api_token: Optional[str] = None,
    core: Optional[LogStormCore] = None,
) -> FastAPI:
    """Create a LogStorm API app with explicit or env-based settings."""
    runtime = core or LogStormCore.from_sources(
        collector_db_path=db_path,
        api_token=api_token,
    )
    app = FastAPI(title="LogStorm API", version="0.1.0")
    app.state.core = runtime
    app.state.db_path = runtime.settings.api.collector_db_path
    app.state.api_token = runtime.settings.api.api_token
    app.state.allow_default_schedule = (
        runtime.settings.api.allow_default_schedule
    )
    app.state.photo_path_rewrites = runtime.settings.api.photo_path_rewrites

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/attendance/analyze", dependencies=[Depends(require_token)])
    def analyze_attendance(payload: AttendanceAnalyzePayload):
        data = payload.model_dump()
        if data.get("schedule") is None:
            if not app.state.allow_default_schedule:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=(
                        "schedule is required because "
                        "LOGSTORM_ALLOW_DEFAULT_SCHEDULE=false"
                    ),
                )
            data["schedule"] = app.state.core.default_schedule_payload()

        request = AttendanceAnalysisRequest.from_dict(data)
        repository = app.state.core.collector_repository()
        raw_events = repository.load_raw_events(
            start=request.period_start.isoformat(),
            end=f"{request.period_end.isoformat()}T23:59:59",
        )
        events_df = LogsCamLoader.load_events(raw_events)
        events_df = LogsCamLoader.filter_valid_passes(events_df)
        response = EusrrAttendanceService(events_df).analyze(request)
        result = response.to_dict()

        overrides = app.state.core.attendance_override_repository().load_for_period(
            employee_id=request.employee_id,
            start=request.period_start,
            end=request.period_end,
        )
        _apply_manual_overrides(result["records"], overrides)
        return result

    @app.patch(
        "/attendance/overrides/{employee_id}/{record_date}",
        dependencies=[Depends(require_token)],
    )
    def update_attendance_override(
        employee_id: str,
        record_date: date,
        payload: AttendanceManualOverridePayload,
    ):
        data = payload.model_dump(exclude_unset=True)
        source = str(data.pop("source", "eusrr") or "eusrr")
        note = data.pop("note", None)
        override = app.state.core.attendance_override_repository().upsert(
            employee_id=employee_id,
            record_date=record_date,
            patch_data=data,
            source=source,
            note=note,
        )
        return attendance_override_to_dict(override)

    @app.get(
        "/attendance/events/day/",
        response_model=list[AttendanceDayEvent],
        dependencies=[Depends(require_token)],
    )
    def attendance_day_events(employee_id: str, date: date):
        repository = app.state.core.collector_repository()
        events = repository.load_raw_events(
            start=date.isoformat(),
            end=f"{date.isoformat()}T23:59:59",
            employee_id=employee_id,
        )
        return [_event_to_day_event(event) for event in events]

    @app.get(
        "/attendance/events/photos/{event_key}/",
        dependencies=[Depends(require_token)],
    )
    def attendance_event_photo(event_key: str):
        device, serial_no = _decode_event_key(event_key)
        event = app.state.core.collector_repository().get_event(
            device=device,
            serial_no=serial_no,
        )
        if event is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found",
            )

        event_data = event.to_event_dict()
        image_path = event_data.get("_imagePath")
        if not image_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event photo not found",
            )

        path = _find_existing_photo_path(
            str(image_path),
            app.state.photo_path_rewrites,
        )
        if path is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event photo file not found",
            )

        media_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
        return FileResponse(path, media_type=media_type, filename=path.name)

    return app


app = create_app()


def _apply_manual_overrides(records: list[dict[str, Any]], overrides) -> None:
    for record in records:
        override = overrides.get(str(record.get("date")))
        if override is None:
            record["manual_edited"] = False
            record["manual_edit_payload"] = {}
            continue

        patch = override.patch_dict()
        record.update(patch)
        _normalize_issues_after_patch(record, patch)
        record["manual_edited"] = True
        record["manual_edit_payload"] = patch
        record["manual_edit_source"] = override.source
        record["manual_edited_at"] = override.updated_at


def _normalize_issues_after_patch(
    record: dict[str, Any],
    patch: dict[str, Any],
) -> None:
    for flag, markers in ISSUE_MARKERS.items():
        if patch.get(flag) is not False:
            continue
        for field in ("statuses", "employee_issues"):
            record[field] = _without_issue_markers(record.get(field), markers)


def _without_issue_markers(value: Any, markers: tuple[str, ...]) -> list[Any]:
    if not isinstance(value, list):
        return []
    return [
        item
        for item in value
        if not any(marker in str(item).lower() for marker in markers)
    ]


def _encode_event_key(device: str, serial_no: int) -> str:
    payload = json.dumps(
        {"device": device, "serial_no": serial_no},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _decode_event_key(event_key: str) -> tuple[str, int]:
    try:
        padding = "=" * (-len(event_key) % 4)
        payload = base64.urlsafe_b64decode(f"{event_key}{padding}".encode("ascii"))
        data = json.loads(payload.decode("utf-8"))
        device = str(data["device"])
        serial_no = int(data["serial_no"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        ) from exc
    return device, serial_no


def _find_existing_photo_path(
    image_path: str,
    rewrites: list[tuple[str, str]],
) -> Optional[Path]:
    for candidate in _photo_path_candidates(image_path, rewrites):
        if candidate.is_file():
            return candidate
    return None


def _photo_path_candidates(
    image_path: str,
    rewrites: list[tuple[str, str]],
) -> list[Path]:
    candidates = [Path(image_path).expanduser()]
    normalized_path = _normalize_photo_path(image_path)
    for source, target in rewrites:
        normalized_source = _normalize_photo_path(source).rstrip("/")
        if not normalized_source:
            continue
        if (
            normalized_path == normalized_source
            or normalized_path.startswith(f"{normalized_source}/")
        ):
            suffix = normalized_path[len(normalized_source):].lstrip("/")
            rewritten = Path(target).expanduser()
            if suffix:
                rewritten = rewritten.joinpath(*suffix.split("/"))
            candidates.append(rewritten)
    return candidates


def _normalize_photo_path(value: str) -> str:
    return str(value).replace("\\", "/").rstrip("/")


def _event_to_day_event(event: dict[str, Any]) -> dict[str, Any]:
    device = str(event.get("_device") or "")
    serial_no = int(event.get("serialNo") or 0)
    event_key = _encode_event_key(device, serial_no)
    time_value = str(event.get("time") or "")
    time_label = _format_event_time_label(time_value)
    caption = EventMapper.get_event_description(
        int(event.get("major") or 0),
        int(event.get("minor") or 0),
    )
    has_photo = bool(event.get("_imagePath"))
    return {
        "event_key": event_key,
        "time": time_value,
        "time_label": time_label,
        "caption": caption,
        "device": device,
        "device_name": str(event.get("_device_name") or device or "Устройство"),
        "serial_no": serial_no,
        "has_photo": has_photo,
        "photo_url": (
            f"/attendance/events/photos/{event_key}/" if has_photo else None
        ),
    }


def _format_event_time_label(value: str) -> str:
    if "T" not in value:
        return value[:8] if value else "-"
    return value.split("T", 1)[1][:8] or "-"
