#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Repository for manual attendance corrections."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from core.db import create_collector_engine
from core.models import AttendanceManualOverride


class AttendanceManualOverrideRepository:
    """Store and read manual attendance corrections through SQLAlchemy."""

    def __init__(
        self,
        db_path_or_url: str,
        *,
        engine: Engine | None = None,
    ):
        self.db_path_or_url = db_path_or_url
        self.engine = engine or self._create_engine(db_path_or_url)

    @staticmethod
    def _create_engine(db_path_or_url: str) -> Engine:
        return create_collector_engine(db_path_or_url, role="api")

    def upsert(
        self,
        *,
        employee_id: str,
        record_date: date | str,
        patch_data: dict[str, Any],
        source: str = "eusrr",
        note: str | None = None,
    ) -> AttendanceManualOverride:
        employee_id = str(employee_id)
        date_value = _format_date(record_date)
        updated_at = datetime.now(UTC).isoformat()
        patch_json = json.dumps(patch_data, ensure_ascii=False, sort_keys=True)

        with Session(self.engine) as session:
            override = session.scalar(
                select(AttendanceManualOverride).where(
                    AttendanceManualOverride.employee_id == employee_id,
                    AttendanceManualOverride.date == date_value,
                )
            )
            if override is None:
                override = AttendanceManualOverride(
                    employee_id=employee_id,
                    date=date_value,
                    patch_data=patch_json,
                    source=source,
                    note=note,
                    updated_at=updated_at,
                )
                session.add(override)
            else:
                override.patch_data = patch_json
                override.source = source
                override.note = note
                override.updated_at = updated_at

            session.commit()
            session.refresh(override)
            return override

    def load_for_period(
        self,
        *,
        employee_id: str,
        start: date | str,
        end: date | str,
    ) -> dict[str, AttendanceManualOverride]:
        with Session(self.engine) as session:
            rows = session.scalars(
                select(AttendanceManualOverride)
                .where(
                    AttendanceManualOverride.employee_id == str(employee_id),
                    AttendanceManualOverride.date >= _format_date(start),
                    AttendanceManualOverride.date <= _format_date(end),
                )
                .order_by(AttendanceManualOverride.date)
            ).all()
            return {row.date: row for row in rows}


def attendance_override_to_dict(
    override: AttendanceManualOverride,
) -> dict[str, Any]:
    return {
        "id": override.id,
        "employee_id": override.employee_id,
        "date": override.date,
        "patch": override.patch_dict(),
        "source": override.source,
        "note": override.note,
        "updated_at": override.updated_at,
    }


def _format_date(value: date | str) -> str:
    if isinstance(value, date):
        return value.isoformat()
    return str(value)
