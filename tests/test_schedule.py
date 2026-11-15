"""Unit tests for pure schedule calculations."""

from datetime import time

import pytest

from custom_components.heat_pump_schedule.schedule import (
    active_period_index,
    parse_time,
    time_to_seconds,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (time(0, 0), 0),
        (time(6, 30, 15), 23415),
        (time(23, 59, 59), 86399),
    ],
)
def test_time_to_seconds(value: time, expected: int) -> None:
    """Wall-clock times are converted to seconds since midnight."""
    assert time_to_seconds(value) == expected


def test_parse_time() -> None:
    """Stored ISO times are parsed including seconds."""
    assert parse_time("06:15:30") == time(6, 15, 30)


@pytest.mark.parametrize(
    ("current", "expected_index"),
    [
        pytest.param(time(5, 59), 3, id="previous-day-period-before-first"),
        pytest.param(time(6, 0), 0, id="exact-boundary"),
        pytest.param(time(17, 0), 1, id="disabled-period-is-ignored"),
        pytest.param(time(23, 30), 3, id="last-period"),
    ],
)
def test_active_period_wraps_across_midnight(
    current: time, expected_index: int
) -> None:
    """The most recently started enabled period wins modulo midnight."""
    periods = [
        {"enabled": True, "start": "06:00:00"},
        {"enabled": True, "start": "12:00:00"},
        {"enabled": False, "start": "16:00:00"},
        {"enabled": True, "start": "22:00:00"},
    ]

    assert active_period_index(periods, current) == expected_index


def test_active_period_is_independent_of_list_order() -> None:
    """Periods do not need to be stored in chronological order."""
    periods = [
        {"enabled": True, "start": "18:00:00"},
        {"enabled": True, "start": "06:00:00"},
        {"enabled": True, "start": "12:00:00"},
    ]

    assert active_period_index(periods, time(13, 0)) == 2


def test_no_active_period_when_all_are_disabled() -> None:
    """A schedule without enabled periods has no active target."""
    periods = [
        {"enabled": False, "start": "00:00:00"},
        {"enabled": False, "start": "12:00:00"},
    ]

    assert active_period_index(periods, time(13, 0)) is None
