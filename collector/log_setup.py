#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Collector logging setup."""

from __future__ import annotations

import logging


def setup_logging(log_file: str, verbose: bool = False) -> logging.Logger:
    """Configure collector logger for file and console output."""
    logger = logging.getLogger("collector")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG if verbose else logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    return logger
