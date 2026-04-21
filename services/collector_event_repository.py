#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Repository for reading collector events through SQLAlchemy."""

import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote

from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from models import CollectorEvent, CollectorState


class CollectorEventRepository:
    """Read-only repository for collector SQLite or SQLAlchemy URLs."""

    def __init__(self, db_path_or_url: str):
        self.db_path_or_url = db_path_or_url
        self.engine = self._create_engine(db_path_or_url)

    @staticmethod
    def _create_engine(db_path_or_url: str) -> Engine:
        if "://" in db_path_or_url:
            url = db_path_or_url
        else:
            path = Path(db_path_or_url).expanduser()
            if not path.is_absolute():
                path = Path.cwd() / path
            url = f"sqlite:///{quote(str(path))}"
        return create_engine(url)

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

    def count_events(self) -> int:
        with Session(self.engine) as session:
            return len(session.scalars(select(CollectorEvent)).all())

    def get_states(self) -> list[CollectorState]:
        with Session(self.engine) as session:
            return list(
                session.scalars(
                    select(CollectorState).order_by(CollectorState.device)
                )
            )
