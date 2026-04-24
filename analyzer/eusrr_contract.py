#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Service-level contract for EUSRR attendance analysis requests."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Optional

import pandas as pd

from core.models import AttendanceRecord, WorkSchedule
from analyzer.service import AttendanceService


@dataclass(frozen=True)
class AttendanceAnalysisRequest:
    """Input DTO for EUSRR -> LogStorm attendance analysis."""

    employee_id: str
    period_start: date
    period_end: date
    schedule: WorkSchedule
    display_name: Optional[str] = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AttendanceAnalysisRequest":
        employee_id = str(payload["employee_id"])
        period_start = _parse_date(payload["period_start"])
        period_end = _parse_date(payload["period_end"])
        if period_start > period_end:
            raise ValueError("period_start must be less than or equal to period_end")

        schedule_payload = payload["schedule"]
        schedule = WorkSchedule.from_preferences({
            "start_time": schedule_payload["start_time"],
            "end_time": schedule_payload["end_time"],
            "expected_hours": schedule_payload["expected_hours"],
            "workdays": schedule_payload.get("workdays", []),
            "date_overrides": schedule_payload.get("date_overrides", []),
        })

        return cls(
            employee_id=employee_id,
            period_start=period_start,
            period_end=period_end,
            schedule=schedule,
            display_name=payload.get("display_name"),
        )


@dataclass(frozen=True)
class AttendanceAnalysisResponse:
    """Output DTO for LogStorm -> EUSRR attendance analysis."""

    employee_id: str
    period_start: date
    period_end: date
    records: list[AttendanceRecord]

    def to_dict(self) -> dict[str, Any]:
        return {
            "employee_id": self.employee_id,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "records": [
                attendance_record_to_dict(record)
                for record in self.records
            ],
        }


class EusrrAttendanceService:
    """Analyze collector events using the schedule supplied by EUSRR."""

    REQUIRED_COLUMNS = ["timestamp", "date", "name", "display_name"]

    def __init__(self, events_df: pd.DataFrame):
        self.events_df = self._ensure_columns(events_df)

    def analyze(
        self, request: AttendanceAnalysisRequest
    ) -> AttendanceAnalysisResponse:
        period_df = self._filter_period(request)
        prefs = {
            request.employee_id: {
                "display_name": request.display_name or request.employee_id,
                "start_time": request.schedule.start_time.strftime("%H:%M"),
                "end_time": request.schedule.end_time.strftime("%H:%M"),
                "expected_hours": request.schedule.expected_hours,
                "workdays": request.schedule.workdays,
            }
        }

        records = AttendanceService(period_df, prefs).analyze_user_period(
            request.employee_id,
            request.period_start,
            request.period_end,
            request.schedule,
            display_name=request.display_name,
        )
        return AttendanceAnalysisResponse(
            employee_id=request.employee_id,
            period_start=request.period_start,
            period_end=request.period_end,
            records=records,
        )

    def _filter_period(self, request: AttendanceAnalysisRequest) -> pd.DataFrame:
        if self.events_df.empty:
            return self.events_df.copy()

        mask = (
            (self.events_df["date"] >= request.period_start)
            & (self.events_df["date"] <= request.period_end)
        )
        return self.events_df.loc[mask].copy()

    @classmethod
    def _ensure_columns(cls, df: pd.DataFrame) -> pd.DataFrame:
        result = df.copy()
        for column in cls.REQUIRED_COLUMNS:
            if column not in result.columns:
                result[column] = pd.Series(dtype="object")
        result["name"] = result["name"].astype(str)
        return result


def _parse_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value), "%Y-%m-%d").date()


def attendance_record_to_dict(record: AttendanceRecord) -> dict[str, Any]:
    """Serialize an attendance record for machine-readable API responses."""
    return {
        "date": record.date.isoformat(),
        "employee_id": record.user_name,
        "display_name": record.display_name,
        "arrival_time": (
            record.arrival_time.isoformat() if record.arrival_time else None
        ),
        "departure_time": (
            record.departure_time.isoformat() if record.departure_time else None
        ),
        "work_hours": round(record.work_hours, 2),
        "appearances": record.appearances,
        "weekday": record.weekday,
        "is_workday": record.is_workday,
        "schedule_start": record.schedule_start.strftime("%H:%M"),
        "schedule_end": record.schedule_end.strftime("%H:%M"),
        "expected_hours": record.expected_hours,
        "is_late": record.is_late,
        "late_minutes": record.late_minutes,
        "is_early_leave": record.is_early_leave,
        "early_leave_minutes": record.early_leave_minutes,
        "is_underwork": record.is_underwork,
        "is_overtime": record.is_overtime,
        "technical_issues": list(record.technical_issues),
        "employee_issues": list(record.employee_issues),
    }
