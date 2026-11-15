"""Unit tests for schedule persistence and climate writes."""

from datetime import UTC, datetime

import pytest
from typing import Any

from homeassistant.components.climate.const import (
    DOMAIN as CLIMATE_DOMAIN,
)
from homeassistant.components.climate.const import (
    SERVICE_SET_TEMPERATURE,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    ATTR_TEMPERATURE,
    STATE_UNAVAILABLE,
)
from homeassistant.core import HomeAssistant, ServiceCall
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.heat_pump_schedule.const import (
    CONF_ENABLED,
    CONF_STANDARD_TEMPERATURE,
    CONF_STANDARD_TEMPERATURE_ENABLED,
    CONF_PERIOD_COUNT,
    CONF_PERIODS,
    CONF_TARGET_ENTITY,
    DOMAIN,
    PERIOD_ENABLED,
    PERIOD_START,
    PERIOD_TEMPERATURE,
    PERIOD_USE_STANDARD_TEMPERATURE,
)
from custom_components.heat_pump_schedule.schedule_manager import ScheduleManager

TARGET = "climate.heating"


def _set_target(
    hass: HomeAssistant,
    *,
    target_temperature: float = 25.0,
    state: str = "heat",
) -> None:
    """Create the target climate state used by manager tests."""
    hass.states.async_set(
        TARGET,
        state,
        {
            ATTR_SUPPORTED_FEATURES: 1,
            ATTR_TEMPERATURE: target_temperature,
            "min_temp": 10.0,
            "max_temp": 55.0,
            "target_temp_step": 0.5,
            "temperature_unit": "°C",
        },
    )


def _entry(hass: HomeAssistant, *, enabled: bool = True) -> MockConfigEntry:
    """Create and register a two-period config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=TARGET,
        data={CONF_TARGET_ENTITY: TARGET, CONF_PERIOD_COUNT: 2},
        options={
            CONF_ENABLED: enabled,
            CONF_PERIOD_COUNT: 2,
            CONF_PERIODS: [
                {
                    PERIOD_ENABLED: True,
                    PERIOD_START: "06:00:00",
                    PERIOD_TEMPERATURE: 30.0,
                },
                {
                    PERIOD_ENABLED: True,
                    PERIOD_START: "22:00:00",
                    PERIOD_TEMPERATURE: 32.0,
                },
            ],
        },
    )
    entry.add_to_hass(hass)
    return entry


def _capture_temperature_calls(
    hass: HomeAssistant,
) -> list[dict[str, Any]]:
    """Register a fake climate service and capture its calls."""
    calls: list[dict[str, Any]] = []

    async def handle_set_temperature(call: ServiceCall) -> None:
        calls.append(dict(call.data))

    hass.services.async_register(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        handle_set_temperature,
    )
    return calls


async def test_apply_uses_previous_day_period_after_midnight(
    hass: HomeAssistant,
) -> None:
    """At night, the period beginning before midnight remains active."""
    _set_target(hass)
    manager = ScheduleManager(hass, _entry(hass))
    calls = _capture_temperature_calls(hass)

    await manager.async_apply(datetime(2026, 1, 2, 1, 0, tzinfo=UTC))

    assert calls == [
        {
            ATTR_ENTITY_ID: TARGET,
            ATTR_TEMPERATURE: 32.0,
        }
    ]
    assert manager.last_applied_temperature == 32.0
    assert manager.last_error is None


async def test_apply_skips_temperature_already_set(
    hass: HomeAssistant,
) -> None:
    """The manager avoids writing the same target every minute."""
    _set_target(hass, target_temperature=30.0)
    manager = ScheduleManager(hass, _entry(hass))
    calls = _capture_temperature_calls(hass)

    await manager.async_apply(datetime(2026, 1, 2, 8, 0, tzinfo=UTC))

    assert calls == []
    assert manager.last_sync_check is not None
    assert manager.last_temperature_sent is None


async def test_force_apply_works_while_schedule_is_disabled(
    hass: HomeAssistant,
) -> None:
    """The apply-now button can test a disabled schedule."""
    _set_target(hass)
    manager = ScheduleManager(hass, _entry(hass, enabled=False))
    calls = _capture_temperature_calls(hass)
    now = datetime(2026, 1, 2, 8, 0, tzinfo=UTC)

    await manager.async_apply(now)
    assert calls == []

    await manager.async_apply(now, force=True)
    assert calls == [
        {
            ATTR_ENTITY_ID: TARGET,
            ATTR_TEMPERATURE: 30.0,
        }
    ]
    assert manager.last_sync_check is not None
    assert manager.last_temperature_sent is not None
    assert manager.last_temperature_sent >= manager.last_sync_check


async def test_unavailable_target_sets_diagnostic_error(
    hass: HomeAssistant,
) -> None:
    """No service call is made when the selected climate is unavailable."""
    _set_target(hass, state=STATE_UNAVAILABLE)
    manager = ScheduleManager(hass, _entry(hass))
    calls = _capture_temperature_calls(hass)

    await manager.async_apply(datetime(2026, 1, 2, 8, 0, tzinfo=UTC))

    assert calls == []
    assert manager.last_error == "target_unavailable"
    assert manager.status == "target_unavailable"


async def test_period_temperature_is_aligned_and_persisted(
    hass: HomeAssistant,
) -> None:
    """Period edits respect target limits and survive a reload."""
    _set_target(hass)
    entry = _entry(hass, enabled=False)
    manager = ScheduleManager(hass, entry)

    await manager.async_set_period_temperature(0, 31.3)

    assert manager.period_temperature(0) == 31.5
    assert entry.options[CONF_PERIODS][0][PERIOD_TEMPERATURE] == 31.5


def test_invalid_stored_values_are_normalized(hass: HomeAssistant) -> None:
    """Bad stored values fall back safely and temperatures are clamped."""
    _set_target(hass, target_temperature=24.0)
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=TARGET,
        data={CONF_TARGET_ENTITY: TARGET, CONF_PERIOD_COUNT: 2},
        options={
            CONF_PERIOD_COUNT: 2,
            CONF_PERIODS: [
                {
                    PERIOD_ENABLED: True,
                    PERIOD_START: "not-a-time",
                    PERIOD_TEMPERATURE: 100,
                },
                {
                    PERIOD_ENABLED: True,
                    PERIOD_START: "12:00:00",
                    PERIOD_TEMPERATURE: "invalid",
                },
            ],
        },
    )
    entry.add_to_hass(hass)

    manager = ScheduleManager(hass, entry)

    assert manager.period_start(0).isoformat() == "00:00:00"
    assert manager.period_temperature(0) == 55.0
    assert manager.period_temperature(1) == 24.0


@pytest.mark.parametrize("enabled,standard_enabled,expected", [
    (False, False, None), (False, True, 28.5),
    (True, False, 30.0), (True, True, 30.0),
])
async def test_control_modes(
    hass: HomeAssistant, enabled: bool, standard_enabled: bool, expected: float | None,
) -> None:
    """Schedule control takes priority and both off preserves the target."""
    _set_target(hass)
    entry = _entry(hass, enabled=enabled)
    hass.config_entries.async_update_entry(entry, options={
        **entry.options, CONF_STANDARD_TEMPERATURE: 28.3,
        CONF_STANDARD_TEMPERATURE_ENABLED: standard_enabled,
    })
    manager = ScheduleManager(hass, entry)
    calls = _capture_temperature_calls(hass)
    await manager.async_apply(datetime(2026, 1, 2, 8, 0, tzinfo=UTC))
    assert [call[ATTR_TEMPERATURE] for call in calls] == ([] if expected is None else [expected])
    assert manager.active_period_index(datetime(2026, 1, 2, 8, 0, tzinfo=UTC)) == 0
    assert manager.active_period_index(datetime(2026, 1, 2, 23, 0, tzinfo=UTC)) == 1
    assert manager.active_period_index(datetime(2026, 1, 3, 1, 0, tzinfo=UTC)) == 1
    if not enabled and standard_enabled:
        assert manager.status == "standard_temperature"
        assert manager.desired_temperature() == 28.5


async def test_standard_temperature_transitions_and_reload(hass: HomeAssistant) -> None:
    """Switches apply immediately, persist across reload, and stop writing when off."""
    _set_target(hass)
    entry = _entry(hass)
    hass.config_entries.async_update_entry(entry, options={
        **entry.options, CONF_STANDARD_TEMPERATURE: 28.0,
    })
    manager = ScheduleManager(hass, entry)
    calls = _capture_temperature_calls(hass)
    await manager.async_set_standard_temperature_enabled(True)
    assert calls[-1][ATTR_TEMPERATURE] in (30.0, 32.0)
    await manager.async_set_enabled(False)
    assert calls[-1][ATTR_TEMPERATURE] == 28.0
    restored = ScheduleManager(hass, entry)
    await restored.async_setup()
    await hass.async_block_till_done()
    assert restored.standard_temperature_enabled
    assert restored.standard_temperature == 28.0
    assert not restored.enabled
    assert calls[-1][ATTR_TEMPERATURE] == 28.0
    _set_target(hass, target_temperature=28.0)
    calls.clear()
    await restored.async_apply()
    assert calls == []
    _set_target(hass, target_temperature=24.0)
    await restored.async_apply()
    assert calls[-1][ATTR_TEMPERATURE] == 28.0
    await restored.async_set_standard_temperature_enabled(False)
    calls.clear()
    await restored.async_apply()
    assert calls == []
    await restored.async_set_enabled(True)
    assert calls[-1][ATTR_TEMPERATURE] in (30.0, 32.0)
    await restored.async_unload()


async def test_standard_temperature_without_periods_and_unavailable_target(hass: HomeAssistant) -> None:
    """Constant mode does not depend on periods and retains error diagnostics."""
    _set_target(hass)
    manager = ScheduleManager(hass, _entry(hass, enabled=False))
    calls = _capture_temperature_calls(hass)
    for period in manager.periods:
        period[PERIOD_ENABLED] = False
    assert manager.active_period_index() is None
    manager.standard_temperature = 28.0
    await manager.async_set_standard_temperature_enabled(True)
    assert calls[-1][ATTR_TEMPERATURE] == 28.0
    _set_target(hass, state=STATE_UNAVAILABLE)
    calls.clear()
    await manager.async_apply()
    assert calls == []
    assert manager.status == "target_unavailable"
    _set_target(hass)
    await manager.async_apply(force=True)
    assert calls[-1][ATTR_TEMPERATURE] == 28.0
    assert manager.status == "standard_temperature"


def test_new_entry_defaults_to_both_controls_off(hass: HomeAssistant) -> None:
    """Fresh installations must not change the climate target automatically."""
    _set_target(hass)
    entry = MockConfigEntry(domain=DOMAIN, data={
        CONF_TARGET_ENTITY: TARGET, CONF_PERIOD_COUNT: 2,
        CONF_STANDARD_TEMPERATURE: 28.0,
    })
    manager = ScheduleManager(hass, entry)
    assert not manager.enabled
    assert not manager.standard_temperature_enabled
    assert manager.standard_temperature == 28.0


@pytest.mark.parametrize("fallback_enabled", [False, True])
async def test_linked_period_follows_standard_temperature(
    hass: HomeAssistant, fallback_enabled: bool,
) -> None:
    """Linked periods resolve the latest standard value independently of fallback control."""
    _set_target(hass)
    entry = _entry(hass)
    hass.config_entries.async_update_entry(entry, options={
        **entry.options,
        CONF_STANDARD_TEMPERATURE: 28.0,
        CONF_STANDARD_TEMPERATURE_ENABLED: fallback_enabled,
        CONF_PERIODS: [
            {**entry.options[CONF_PERIODS][0], PERIOD_USE_STANDARD_TEMPERATURE: True},
            entry.options[CONF_PERIODS][1],
        ],
    })
    manager = ScheduleManager(hass, entry)
    calls = _capture_temperature_calls(hass)
    day = datetime(2026, 1, 2, 8, 0, tzinfo=UTC)
    night = datetime(2026, 1, 2, 23, 0, tzinfo=UTC)
    await manager.async_apply(day)
    assert calls[-1][ATTR_TEMPERATURE] == 28.0
    assert manager.period_temperature(0) == 28.0
    assert manager.period_temperature(1) == 32.0
    await manager.async_apply(night)
    assert calls[-1][ATTR_TEMPERATURE] == 32.0
    hass.config_entries.async_update_entry(entry, options={
        **manager.options_snapshot(), CONF_STANDARD_TEMPERATURE: 29.5,
    })
    restored = ScheduleManager(hass, entry)
    await restored.async_apply(day)
    assert calls[-1][ATTR_TEMPERATURE] == 29.5
    assert restored.period_temperature(0) == 29.5
    assert restored.periods[0][PERIOD_TEMPERATURE] == 30.0
    assert restored.period_temperature(1) == 32.0
