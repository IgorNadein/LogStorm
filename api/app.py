#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FastAPI application for LogStorm attendance analysis."""

import os
from datetime import date
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

from config import DEFAULT_SCHEDULE
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
    schedule: Optional[SchedulePayload] = None
    display_name: Optional[str] = None


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


def _default_schedule_payload() -> dict:
    return {
        "start_time": os.getenv(
            "LOGSTORM_DEFAULT_START_TIME",
            DEFAULT_SCHEDULE["start_time"],
        ),
        "end_time": os.getenv(
            "LOGSTORM_DEFAULT_END_TIME",
            DEFAULT_SCHEDULE["end_time"],
        ),
        "expected_hours": float(os.getenv(
            "LOGSTORM_DEFAULT_EXPECTED_HOURS",
            str(DEFAULT_SCHEDULE["work_hours"]),
        )),
        "workdays": [
            item.strip()
            for item in os.getenv(
                "LOGSTORM_DEFAULT_WORKDAYS",
                ",".join(DEFAULT_SCHEDULE["workdays"]),
            ).split(",")
            if item.strip()
        ],
        "date_overrides": [],
    }


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
    app.state.allow_default_schedule = _env_bool(
        "LOGSTORM_ALLOW_DEFAULT_SCHEDULE", True
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
            data["schedule"] = _default_schedule_payload()

        request = AttendanceAnalysisRequest.from_dict(data)
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
