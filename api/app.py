#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FastAPI application for LogStorm attendance analysis."""

import os
from datetime import date
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

from services import AttendanceAnalysisRequest, EusrrAttendanceService
from services.collector_event_repository import CollectorEventRepository
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
    schedule: SchedulePayload
    display_name: Optional[str] = None


def create_app(
    db_path: Optional[str] = None,
    api_token: Optional[str] = None,
) -> FastAPI:
    """Create a LogStorm API app with explicit or env-based settings."""
    app = FastAPI(title="LogStorm API", version="0.1.0")
    app.state.db_path = db_path or os.getenv(
        "LOGSTORM_COLLECTOR_DB_PATH", "events.db"
    )
    app.state.api_token = (
        api_token if api_token is not None
        else os.getenv("LOGSTORM_API_TOKEN", "")
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
        request = AttendanceAnalysisRequest.from_dict(payload.model_dump())
        repository = CollectorEventRepository(app.state.db_path)
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
