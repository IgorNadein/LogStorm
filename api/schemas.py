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
    aliases: list[str] = Field(default_factory=list)


class AttendanceManualOverridePayload(BaseModel):
    arrival_time: Optional[str] = None
    departure_time: Optional[str] = None
    work_hours: Optional[float] = None
    expected_hours: Optional[float] = None
    is_workday: Optional[bool] = None
    effective_is_workday: Optional[bool] = None
    is_late: Optional[bool] = None
    late_minutes: Optional[int] = None
    is_early_leave: Optional[bool] = None
    early_leave_minutes: Optional[int] = None
    is_underwork: Optional[bool] = None
    underwork_hours: Optional[float] = None
    is_overtime: Optional[bool] = None
    overtime_hours: Optional[float] = None
    is_absent: Optional[bool] = None
    source: str = "eusrr"
    note: Optional[str] = None


class AttendanceDayEvent(BaseModel):
    event_key: str
    time: str
    time_label: str
    caption: str
    device: str
    device_name: str
    serial_no: int
    has_photo: bool
    photo_url: Optional[str] = None
