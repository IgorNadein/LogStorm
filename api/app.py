#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FastAPI application for LogStorm attendance analysis."""

from datetime import date
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException, status

from core import LogStormCore
from core.repositories import attendance_override_to_dict
from analyzer import AttendanceAnalysisRequest, EusrrAttendanceService
from analyzer.logscam_loader import LogsCamLoader
from api.auth import require_token
from api.schemas import (
    AttendanceAnalyzePayload,
    AttendanceManualOverridePayload,
)


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
            employee_id=request.employee_id,
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
