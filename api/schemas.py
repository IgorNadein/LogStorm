"""HTTP API schemas."""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


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
