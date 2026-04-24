"""
Storage layer for collector events.

Writes raw NDJSON and stores structured state through SQLAlchemy models.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional
from urllib.parse import unquote, urlparse

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from core.db import build_db_url, create_collector_engine
from core.models import (
    AttendanceManualOverride,
    Base,
    CollectorEvent,
    CollectorState,
)


class EventStorage:
    """Double storage: NDJSON journal + ORM-backed relational storage."""

    def __init__(self, ndjson_path: str, sqlite_path: Optional[str] = None):
        """
        Args:
            ndjson_path: Path to the append-only NDJSON journal.
            sqlite_path: Local SQLite path or SQLAlchemy URL for structured DB.
        """
        self.ndjson_path = ndjson_path
        if sqlite_path is None:
            base = os.path.splitext(ndjson_path)[0]
            sqlite_path = f"{base}.db"

        self.sqlite_path = sqlite_path
        self.db_url = build_db_url(sqlite_path)
        self._lock = Lock()

        self._ensure_parent_dirs()
        self._create_engine()
        self._init_schema()

    def _ensure_parent_dirs(self) -> None:
        for path in [self.ndjson_path]:
            directory = os.path.dirname(path)
            if directory:
                os.makedirs(directory, exist_ok=True)

        sqlite_file_path = self._local_sqlite_file_path()
        if sqlite_file_path is not None and sqlite_file_path.parent:
            sqlite_file_path.parent.mkdir(parents=True, exist_ok=True)

    def _create_engine(self) -> None:
        self.engine = create_collector_engine(
            self.sqlite_path,
            role="collector",
            timeout=30.0,
        )
        self.SessionLocal = sessionmaker(self.engine, expire_on_commit=False)

    def _storage_tables(self) -> list[Any]:
        return [
            CollectorEvent.__table__,
            CollectorState.__table__,
            AttendanceManualOverride.__table__,
        ]

    def _is_sqlite_backend(self) -> bool:
        return self.db_url.startswith("sqlite")

    def _local_sqlite_file_path(self) -> Optional[Path]:
        if "://" not in self.sqlite_path:
            return Path(self.sqlite_path).expanduser()

        if not self.db_url.startswith("sqlite:///"):
            return None

        parsed = urlparse(self.db_url)
        if parsed.scheme != "sqlite" or not parsed.path:
            return None
        return Path(unquote(parsed.path))

    def _init_schema(self) -> None:
        Base.metadata.create_all(self.engine, tables=self._storage_tables())
        if self._is_sqlite_backend():
            with self.engine.begin() as conn:
                conn.exec_driver_sql("PRAGMA journal_mode=WAL")
                conn.exec_driver_sql("PRAGMA busy_timeout=30000")

    def write_events(self, events: List[Dict[str, Any]]) -> None:
        """Write events to NDJSON and relational storage."""
        if not events:
            return

        with self._lock:
            with open(self.ndjson_path, "a", encoding="utf-8") as handle:
                for event in events:
                    handle.write(json.dumps(event, ensure_ascii=False) + "\n")

            self._write_sqlite_events(events)

    def _write_sqlite_events(self, events: List[Dict[str, Any]]) -> None:
        """Write events to the relational store."""
        with self.SessionLocal.begin() as session:
            for event in events:
                row = session.get(
                    CollectorEvent,
                    {
                        "device": event.get("_device", ""),
                        "serialNo": event.get("serialNo", 0),
                    },
                )
                if row is None:
                    row = CollectorEvent(
                        device=event.get("_device", ""),
                        serialNo=event.get("serialNo", 0),
                        time=event.get("time", ""),
                        employeeNoString=event.get("employeeNoString", ""),
                        name=event.get("name", ""),
                        event_data=json.dumps(event, ensure_ascii=False),
                        collected_at=event.get("_collected", ""),
                    )
                    session.add(row)
                    continue

                row.time = event.get("time", "")
                row.employeeNoString = event.get("employeeNoString", "")
                row.name = event.get("name", "")
                row.event_data = json.dumps(event, ensure_ascii=False)
                row.collected_at = event.get("_collected", "")

    def update_collector_state(
        self,
        device: str,
        last_serial: int,
        last_collect: Optional[str] = None,
    ) -> None:
        """Update persisted collector cursor for a device."""
        now = datetime.now().isoformat()
        with self.SessionLocal.begin() as session:
            state = session.get(CollectorState, device)
            if state is None:
                state = CollectorState(
                    device=device,
                    last_serial=last_serial,
                    last_collect=last_collect,
                    updated_at=now,
                )
                session.add(state)
                return

            state.last_serial = last_serial
            state.last_collect = last_collect
            state.updated_at = now

    def get_collector_state(self, device: str) -> Optional[Dict[str, Any]]:
        """Return collector cursor for a device."""
        with Session(self.engine) as session:
            state = session.get(CollectorState, device)
            if state is None:
                return None
            return {
                "last_serial": state.last_serial,
                "last_collect": state.last_collect,
                "updated_at": state.updated_at,
            }

    def get_last_serial(self, device: str) -> int:
        """Return highest serialNo for a device or 1 when empty."""
        with Session(self.engine) as session:
            result = session.scalar(
                select(func.max(CollectorEvent.serialNo)).where(
                    CollectorEvent.device == device
                )
            )
            return int(result) if result is not None else 1

    def get_last_serials_all_devices(self) -> Dict[str, int]:
        """Return highest serialNo for each device."""
        with Session(self.engine) as session:
            rows = session.execute(
                select(
                    CollectorEvent.device,
                    func.max(CollectorEvent.serialNo),
                ).group_by(CollectorEvent.device)
            ).all()
            return {device: int(serial) for device, serial in rows if serial is not None}

    def get_event_count(self, device: Optional[str] = None) -> int:
        """Return stored event count."""
        stmt = select(func.count()).select_from(CollectorEvent)
        if device:
            stmt = stmt.where(CollectorEvent.device == device)
        with Session(self.engine) as session:
            return int(session.scalar(stmt) or 0)

    def iter_events_without_images(
        self,
        device: Optional[str] = None,
        limit: Optional[int] = None,
        newest_first: bool = False,
    ):
        """Iterate raw events missing `_imagePath`."""
        stmt = select(CollectorEvent.event_data).where(
            CollectorEvent.event_data.not_like('%"_imagePath"%')
        )
        if device:
            stmt = stmt.where(CollectorEvent.device == device)

        if newest_first:
            stmt = stmt.order_by(
                CollectorEvent.time.desc(),
                CollectorEvent.serialNo.desc(),
                CollectorEvent.device,
            )
        else:
            stmt = stmt.order_by(
                CollectorEvent.device,
                CollectorEvent.time,
                CollectorEvent.serialNo,
            )

        if limit is not None:
            stmt = stmt.limit(int(limit))

        with Session(self.engine) as session:
            for event_data in session.scalars(stmt):
                try:
                    yield json.loads(event_data)
                except json.JSONDecodeError:
                    continue

    def update_event(self, event: Dict[str, Any]) -> None:
        """Update an existing event row in structured storage only."""
        device = event.get("_device", "")
        serial_no = event.get("serialNo", 0)
        with self.SessionLocal.begin() as session:
            row = session.get(
                CollectorEvent,
                {"device": device, "serialNo": serial_no},
            )
            if row is None:
                return

            row.time = event.get("time", "")
            row.employeeNoString = event.get("employeeNoString", "")
            row.name = event.get("name", "")
            row.event_data = json.dumps(event, ensure_ascii=False)
            row.collected_at = event.get("_collected", "")

    def update_event_image(
        self,
        device: str,
        serial_no: int,
        image_path: str,
    ) -> bool:
        """Update only `_imagePath` inside stored event JSON."""
        with self.SessionLocal.begin() as session:
            row = session.get(
                CollectorEvent,
                {"device": device, "serialNo": serial_no},
            )
            if row is None:
                return False

            try:
                event = json.loads(row.event_data)
            except json.JSONDecodeError:
                return False

            event["_imagePath"] = image_path
            row.event_data = json.dumps(event, ensure_ascii=False)
            return True

    def rebuild_sqlite_from_ndjson(self, progress_callback=None) -> int:
        """Rebuild structured storage from the append-only NDJSON journal."""
        if not os.path.exists(self.ndjson_path):
            return 0

        sqlite_file_path = self._local_sqlite_file_path()
        if sqlite_file_path is not None:
            self.engine.dispose()
            if sqlite_file_path.exists():
                sqlite_file_path.unlink()
            self._create_engine()
            self._init_schema()
        else:
            Base.metadata.drop_all(self.engine, tables=self._storage_tables())
            self._init_schema()

        count = 0
        batch: list[dict[str, Any]] = []
        batch_size = 1000

        with open(self.ndjson_path, "r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    event = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue

                batch.append(event)
                count += 1

                if len(batch) >= batch_size:
                    self._write_sqlite_events(batch)
                    batch = []
                    if progress_callback:
                        progress_callback(count)

        if batch:
            self._write_sqlite_events(batch)

        return count
