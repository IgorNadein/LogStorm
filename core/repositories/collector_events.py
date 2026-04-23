#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Repository for reading collector events through SQLAlchemy."""

import os
from collections.abc import Iterator
from typing import Any, Optional

from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from core.db import create_collector_engine
from core.models import CollectorEvent, CollectorState


class CollectorEventRepository:
    """Read-only repository for collector SQLite or SQLAlchemy URLs."""

    def __init__(self, db_path_or_url: str):
        self.db_path_or_url = db_path_or_url
        self.engine = self._create_engine(db_path_or_url)

    @staticmethod
    def _create_engine(db_path_or_url: str) -> Engine:
        return create_collector_engine(db_path_or_url)

    def iter_events(
        self,
        start: Optional[str] = None,
        end: Optional[str] = None,
        devices: Optional[list[str]] = None,
        limit: Optional[int] = None,
        employee_id: Optional[str] = None,
    ) -> Iterator[CollectorEvent]:
        stmt = select(CollectorEvent).order_by(
            CollectorEvent.time,
            CollectorEvent.device,
            CollectorEvent.serialNo,
        )
        if start:
            stmt = stmt.where(CollectorEvent.time >= start)
        if end:
            stmt = stmt.where(CollectorEvent.time <= end)
        if employee_id:
            stmt = stmt.where(CollectorEvent.employeeNoString == str(employee_id))
        if devices:
            stmt = stmt.where(CollectorEvent.device.in_(devices))
        if limit:
            stmt = stmt.limit(limit)

        with Session(self.engine) as session:
            for event in session.scalars(stmt):
                yield event

    def load_raw_events(
        self,
        start: Optional[str] = None,
        end: Optional[str] = None,
        devices: Optional[list[str]] = None,
        limit: Optional[int] = None,
        employee_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        return [
            event.to_event_dict()
            for event in self.iter_events(
                start, end, devices, limit, employee_id
            )
        ]

    def get_event(self, *, device: str, serial_no: int) -> Optional[CollectorEvent]:
        with Session(self.engine) as session:
            return session.get(CollectorEvent, {"device": device, "serialNo": serial_no})

    def count_events(self) -> int:
        with Session(self.engine) as session:
            return int(
                session.scalar(
                    select(func.count()).select_from(CollectorEvent)
                )
                or 0
            )

    def get_states(self) -> list[CollectorState]:
        with Session(self.engine) as session:
            return list(
                session.scalars(
                    select(CollectorState).order_by(CollectorState.device)
                )
            )
