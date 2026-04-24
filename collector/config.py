#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Collector configuration helpers."""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import sys
from pprint import pformat
from typing import Any

try:
    from core import build_collector_config
except ImportError:  # pragma: no cover - direct script execution
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core import build_collector_config


DEFAULT_CONFIG = build_collector_config()


def is_db_url(value: str) -> bool:
    """Return True when value looks like a SQLAlchemy database URL."""
    return "://" in value


def _merge_config(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if (
            isinstance(value, dict)
            and isinstance(merged.get(key), dict)
            and key in {"storage", "images", "request"}
        ):
            merged[key] = _merge_config(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def load_config(config_path: str) -> dict[str, Any]:
    """Load collector configuration from JSON or Python config."""
    if os.path.exists(config_path):
        if config_path.endswith(".py"):
            return load_python_config(config_path)
        with open(config_path, "r", encoding="utf-8") as handle:
            return _merge_config(DEFAULT_CONFIG, json.load(handle))
    return copy.deepcopy(DEFAULT_CONFIG)


def load_python_config(config_path: str) -> dict[str, Any]:
    """Load collector configuration from a Python file with CONFIG dict."""
    spec = importlib.util.spec_from_file_location(
        "logstorm_collector_config",
        config_path,
    )
    if spec is None or spec.loader is None:
        raise ValueError(f"Не удалось загрузить Python config: {config_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    config = getattr(module, "CONFIG", None)
    if not isinstance(config, dict):
        raise ValueError(
            f"Python config должен содержать словарь CONFIG: {config_path}"
        )
    return _merge_config(DEFAULT_CONFIG, config)


def get_app_dir() -> str:
    """Return app directory, including PyInstaller support."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def save_default_config(config_path: str) -> None:
    """Persist default config as JSON or Python module."""
    if not os.path.isabs(config_path):
        config_path = os.path.join(get_app_dir(), config_path)

    with open(config_path, "w", encoding="utf-8") as handle:
        if config_path.endswith(".json"):
            json.dump(DEFAULT_CONFIG, handle, indent=2, ensure_ascii=False)
        else:
            handle.write('"""Local LogStorm collector configuration."""\n\n')
            handle.write("# Keep real credentials out of Git.\n")
            handle.write(f"CONFIG = {pformat(DEFAULT_CONFIG, width=88)}\n")
    print(f"[OK] Создан файл конфигурации: {config_path}")
