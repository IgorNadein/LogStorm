#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared SQLAlchemy engine helpers for collector storage."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


def build_db_url(db_path_or_url: str) -> str:
    """Normalize a local SQLite path or pass through a full SQLAlchemy URL."""
    if "://" in db_path_or_url:
        return db_path_or_url

    path = Path(db_path_or_url).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return f"sqlite:///{quote(str(path))}"


def create_collector_engine(
    db_path_or_url: str,
    *,
    timeout: float = 30.0,
) -> Engine:
    """Create a SQLAlchemy engine for collector storage."""
    url = build_db_url(db_path_or_url)
    engine_kwargs = {}
    if url.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"timeout": timeout}
    return create_engine(url, **engine_kwargs)
