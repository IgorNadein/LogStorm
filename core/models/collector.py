#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SQLAlchemy models for collector storage."""

import json
from typing import Any, Optional

from sqlalchemy import Integer, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for SQLAlchemy collector models."""


class CollectorEvent(Base):
    """Event row collected from an access-control device."""

    __tablename__ = "events"

    device: Mapped[str] = mapped_column(Text, primary_key=True)
    serialNo: Mapped[int] = mapped_column(Integer, primary_key=True)
    time: Mapped[str] = mapped_column(Text, nullable=False)
    employeeNoString: Mapped[Optional[str]] = mapped_column(Text)
    name: Mapped[Optional[str]] = mapped_column(Text)
    event_data: Mapped[str] = mapped_column(Text, nullable=False)
    collected_at: Mapped[str] = mapped_column(Text, nullable=False)

    def to_event_dict(self) -> dict[str, Any]:
        """Return raw event JSON as a dictionary."""
        return json.loads(self.event_data)


class CollectorState(Base):
    """Last successful collection state for a device."""

    __tablename__ = "collector_state"

    device: Mapped[str] = mapped_column(Text, primary_key=True)
    last_serial: Mapped[int] = mapped_column(Integer, nullable=False)
    last_collect: Mapped[Optional[str]] = mapped_column(Text)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class AttendanceManualOverride(Base):
    """Manual attendance correction stored next to collector events."""

    __tablename__ = "attendance_manual_overrides"
    __table_args__ = (
        UniqueConstraint(
            "employee_id",
            "date",
            name="attendance_manual_override_employee_date_unique",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[str] = mapped_column(Text, nullable=False)
    date: Mapped[str] = mapped_column(Text, nullable=False)
    patch_data: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False, default="eusrr")
    note: Mapped[Optional[str]] = mapped_column(Text)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)

    def patch_dict(self) -> dict[str, Any]:
        """Return stored correction JSON as a dictionary."""
        return json.loads(self.patch_data)
