#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared SQLAlchemy engine helpers for collector storage."""

from __future__ import annotations

from threading import Lock
from pathlib import Path
from urllib.parse import quote

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool


_ENGINE_CACHE: dict[tuple[str, str, float], Engine] = {}
_ENGINE_CACHE_LOCK = Lock()


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
    role: str = "api",
    timeout: float = 30.0,
) -> Engine:
    """Create a SQLAlchemy engine for collector storage."""
    url = build_db_url(db_path_or_url)
    cache_key = (url, role, timeout)

    with _ENGINE_CACHE_LOCK:
        cached = _ENGINE_CACHE.get(cache_key)
        if cached is not None:
            return cached

    engine_kwargs = {}
    if url.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"timeout": timeout}
    elif url.startswith("postgresql"):
        if role == "migration":
            engine_kwargs["poolclass"] = NullPool
        elif role == "collector":
            engine_kwargs.update(
                pool_size=1,
                max_overflow=0,
                pool_pre_ping=True,
                pool_recycle=300,
            )
        else:
            engine_kwargs.update(
                pool_size=2,
                max_overflow=0,
                pool_pre_ping=True,
                pool_recycle=300,
            )

    engine = create_engine(url, **engine_kwargs)
    with _ENGINE_CACHE_LOCK:
        existing = _ENGINE_CACHE.setdefault(cache_key, engine)
    return existing
