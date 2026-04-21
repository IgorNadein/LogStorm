"""Compatibility wrapper for ``analyzer.eusrr_contract``."""

from analyzer.eusrr_contract import (
    AttendanceAnalysisRequest,
    AttendanceAnalysisResponse,
    EusrrAttendanceService,
    attendance_record_to_dict,
)

__all__ = [
    "AttendanceAnalysisRequest",
    "AttendanceAnalysisResponse",
    "EusrrAttendanceService",
    "attendance_record_to_dict",
]
