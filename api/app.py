#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FastAPI application for LogStorm attendance analysis."""

from datetime import date
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

from core import LogStormCore
from services import AttendanceAnalysisRequest, EusrrAttendanceService
from services.logscam_loader import LogsCamLoader


class DateOverridePayload(BaseModel):
    date: date
    is_workday: bool
    reason: str = ""
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    expected_hours: Optional[float] = None


class SchedulePayload(BaseModel):
    start_time: str
    end_time: str
    expected_hours: float
    workdays: list[str] = Field(default_factory=list)
    date_overrides: list[DateOverridePayload] = Field(default_factory=list)


class AttendanceAnalyzePayload(BaseModel):
    employee_id: str
    period_start: date
    period_end: date
    schedule: Optional[SchedulePayload] = None
    display_name: Optional[str] = None


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

    def require_token(authorization: Optional[str] = Header(default=None)):
        token = app.state.api_token
        if not token:
            return
        expected = f"Bearer {token}"
        if authorization != expected:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid LogStorm API token",
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
        return response.to_dict()

    return app


app = create_app()
