#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Collector state tracker."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional


class EventTracker:
    """Track per-device collection state and in-memory duplicates."""

    def __init__(self, storage, initial_days: int = 30):
        self.storage = storage
        self.initial_days = initial_days
        self._serials: dict[str, set[int]] = {}

    def is_duplicate(self, device: str, serial: int) -> bool:
        """Fast duplicate check using an in-memory serial cache."""
        if device not in self._serials:
            self._serials[device] = set()

        if serial in self._serials[device]:
            return True

        self._serials[device].add(serial)

        max_cache_size = 10000
        cache_trim_size = 5000
        if len(self._serials[device]) > max_cache_size:
            sorted_serials = sorted(self._serials[device])
            self._serials[device] = set(sorted_serials[-cache_trim_size:])

        return False

    def get_last_collect_time(self, device: str) -> Optional[str]:
        """Return timestamp of last successful collection from storage."""
        state = self.storage.get_collector_state(device)
        return state["last_collect"] if state else None

    def get_last_serial(self, device: str) -> int:
        """Return last collected serialNo, falling back to max event serial."""
        state = self.storage.get_collector_state(device)
        if state and state["last_serial"]:
            return state["last_serial"]
        return self.storage.get_last_serial(device)

    def update_last_serial(self, device: str, serial: int) -> None:
        """Persist last successful serialNo."""
        state = self.storage.get_collector_state(device)
        last_collect = state["last_collect"] if state else None
        self.storage.update_collector_state(device, serial, last_collect)

    def update_last_collect(self, device: str, timestamp: str) -> None:
        """Persist last successful collection timestamp."""
        last_serial = self.get_last_serial(device)
        self.storage.update_collector_state(device, last_serial, timestamp)

    def get_start_time(self, device: str) -> str:
        """Compute collection start time with one-hour overlap."""
        last = self.get_last_collect_time(device)
        if last:
            try:
                dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
                dt = dt - timedelta(hours=1)
                return dt.strftime("%Y-%m-%dT%H:%M:%S")
            except ValueError:
                pass

        start = datetime.now() - timedelta(days=self.initial_days)
        return start.strftime("%Y-%m-%dT%H:%M:%S")
