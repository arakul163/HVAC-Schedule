"""Pure schedule calculations used by the integration and its tests."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import time
from typing import Any

PERIOD_ENABLED = "enabled"
PERIOD_START = "start"


def time_to_seconds(value: time) -> int:
    """Convert a local wall-clock time to seconds since midnight."""
    return value.hour * 3600 + value.minute * 60 + value.second


def parse_time(value: str) -> time:
    """Parse a stored ISO time."""
    return time.fromisoformat(value)


def active_period_index(
    periods: Sequence[dict[str, Any]], current_time: time
) -> int | None:
    """Return the most recently started enabled period.

    Modulo arithmetic makes a period from the previous day remain active after
    midnight until the first enabled period of the new day starts.
    """
    now_seconds = time_to_seconds(current_time)
    best_index: int | None = None
    best_age = 86401

    for index, period in enumerate(periods):
        if not period.get(PERIOD_ENABLED, False):
            continue
        start_seconds = time_to_seconds(parse_time(str(period[PERIOD_START])))
        age = (now_seconds - start_seconds) % 86400
        if age < best_age:
            best_age = age
            best_index = index

    return best_index
