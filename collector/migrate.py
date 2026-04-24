#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Migrate collector relational storage between SQLAlchemy backends."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Iterable, Sequence
from typing import TypeVar

from sqlalchemy import delete, func, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from core.db import create_collector_engine
from core.models import (
    AttendanceManualOverride,
    Base,
    CollectorEvent,
    CollectorState,
)

T = TypeVar("T")


def _storage_tables() -> list[object]:
    return [
        CollectorEvent.__table__,
        CollectorState.__table__,
        AttendanceManualOverride.__table__,
    ]


def _create_schema(engine: Engine) -> None:
    Base.metadata.create_all(engine, tables=_storage_tables())


def _target_has_data(session: Session) -> bool:
    statements = [
        select(func.count()).select_from(CollectorEvent),
        select(func.count()).select_from(CollectorState),
        select(func.count()).select_from(AttendanceManualOverride),
    ]
    return any(int(session.scalar(stmt) or 0) > 0 for stmt in statements)


def _truncate_target(session: Session) -> None:
    session.execute(delete(CollectorEvent))
    session.execute(delete(CollectorState))
    session.execute(delete(AttendanceManualOverride))


def _copy_in_batches(
    source_session: Session,
    target_session: Session,
    stmt,
    factory: Callable[[object], T],
    *,
    batch_size: int,
    progress_callback: Callable[[str, int], None] | None,
    label: str,
) -> int:
    copied = 0
    batch: list[T] = []

    for row in source_session.scalars(stmt).yield_per(batch_size):
        batch.append(factory(row))
        if len(batch) >= batch_size:
            target_session.add_all(batch)
            target_session.commit()
            copied += len(batch)
            batch = []
            if progress_callback:
                progress_callback(label, copied)

    if batch:
        target_session.add_all(batch)
        target_session.commit()
        copied += len(batch)
        if progress_callback:
            progress_callback(label, copied)

    return copied


def _sync_sequences(engine: Engine) -> None:
    if engine.dialect.name != "postgresql":
        return

    sequence_specs = [
        (
            "attendance_manual_overrides",
            "attendance_manual_overrides_id_seq",
        ),
    ]

    with engine.begin() as conn:
        for table_name, sequence_name in sequence_specs:
            conn.execute(
                text(
                    "SELECT setval(:sequence_name, "
                    "COALESCE((SELECT MAX(id) FROM attendance_manual_overrides), 1), "
                    "true)"
                ),
                {"sequence_name": sequence_name},
            )


def migrate_collector_storage(
    source_db: str,
    target_db: str,
    *,
    batch_size: int = 1000,
    overwrite: bool = False,
    progress_callback: Callable[[str, int], None] | None = None,
) -> dict[str, int]:
    """Copy collector relational data between storage backends."""
    source_engine = create_collector_engine(source_db, role="migration")
    target_engine = create_collector_engine(target_db, role="migration")

    _create_schema(target_engine)

    with Session(source_engine) as source_session, Session(target_engine) as target_session:
        if _target_has_data(target_session):
            if not overwrite:
                raise ValueError(
                    "Target collector database is not empty. "
                    "Use --overwrite to replace its contents."
                )
            _truncate_target(target_session)
            target_session.commit()

        counts = {
            "events": _copy_in_batches(
                source_session,
                target_session,
                select(CollectorEvent).order_by(
                    CollectorEvent.device,
                    CollectorEvent.serialNo,
                ),
                lambda row: CollectorEvent(
                    device=row.device,
                    serialNo=row.serialNo,
                    time=row.time,
                    employeeNoString=row.employeeNoString,
                    name=row.name,
                    event_data=row.event_data,
                    collected_at=row.collected_at,
                ),
                batch_size=batch_size,
                progress_callback=progress_callback,
                label="events",
            ),
            "states": _copy_in_batches(
                source_session,
                target_session,
                select(CollectorState).order_by(CollectorState.device),
                lambda row: CollectorState(
                    device=row.device,
                    last_serial=row.last_serial,
                    last_collect=row.last_collect,
                    updated_at=row.updated_at,
                ),
                batch_size=batch_size,
                progress_callback=progress_callback,
                label="states",
            ),
            "overrides": _copy_in_batches(
                source_session,
                target_session,
                select(AttendanceManualOverride).order_by(
                    AttendanceManualOverride.id
                ),
                lambda row: AttendanceManualOverride(
                    id=row.id,
                    employee_id=row.employee_id,
                    date=row.date,
                    patch_data=row.patch_data,
                    source=row.source,
                    note=row.note,
                    updated_at=row.updated_at,
                ),
                batch_size=batch_size,
                progress_callback=progress_callback,
                label="overrides",
            ),
        }

    _sync_sequences(target_engine)
    source_engine.dispose()
    target_engine.dispose()
    return counts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Migrate collector relational storage to another DB backend",
    )
    parser.add_argument("--source-db", required=True, help="Source SQLite path or DB URL")
    parser.add_argument(
        "--target-db",
        help="Optional override for target DB URL/path from project settings",
    )
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Clear target storage before importing",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    from core import build_settings

    settings = build_settings()
    target_db = args.target_db or settings.collector.sqlite_path

    def progress(label: str, copied: int) -> None:
        print(f"[collector-migrate] {label}: {copied}")

    counts = migrate_collector_storage(
        args.source_db,
        target_db,
        batch_size=args.batch_size,
        overwrite=args.overwrite,
        progress_callback=progress,
    )
    print(
        "[collector-migrate] done: "
        f"events={counts['events']}, "
        f"states={counts['states']}, "
        f"overrides={counts['overrides']}"
    )


if __name__ == "__main__":
    main()
