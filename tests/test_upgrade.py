"""Regression tests for upgrading existing installations in place."""

import pytest
from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.heat_pump_schedule.const import (
    CONF_ENABLED,
    CONF_PERIOD_COUNT,
    CONF_PERIODS,
    CONF_STANDARD_TEMPERATURE,
    CONF_STANDARD_TEMPERATURE_ENABLED,
    CONF_TARGET_ENTITY,
    DOMAIN,
    PERIOD_ENABLED,
    PERIOD_START,
    PERIOD_TEMPERATURE,
    PERIOD_USE_STANDARD_TEMPERATURE,
)


@pytest.mark.parametrize("enabled", [False, True])
async def test_upgrade_preserves_existing_installation(
    hass: HomeAssistant, enabled: bool,
) -> None:
    """Old entries load and reload without resetting controls or entity IDs."""
    target = "climate.heating"
    hass.states.async_set(target, "heat", {
        ATTR_TEMPERATURE: 25.0,
        "min_temp": 10.0,
        "max_temp": 55.0,
        "target_temp_step": 0.5,
    })
    calls: list[float] = []

    async def capture(call: ServiceCall) -> None:
        calls.append(float(call.data[ATTR_TEMPERATURE]))

    hass.services.async_register("climate", "set_temperature", capture)
    original_data = {CONF_TARGET_ENTITY: target, CONF_PERIOD_COUNT: 2}
    periods = [
        {PERIOD_ENABLED: True, PERIOD_START: "06:00:00", PERIOD_TEMPERATURE: 30.0},
        {PERIOD_ENABLED: False, PERIOD_START: "22:00:00", PERIOD_TEMPERATURE: 32.0},
    ]
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=target,
        version=1,
        data=original_data,
        options={CONF_ENABLED: enabled, CONF_PERIOD_COUNT: 2, CONF_PERIODS: periods},
    )
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    old_switch = registry.async_get_or_create(
        "switch", DOMAIN, f"{target}_schedule_enabled",
        config_entry=entry, suggested_object_id="my_existing_schedule",
    )
    old_period = registry.async_get_or_create(
        "sensor", DOMAIN, f"{target}_period_1_summary",
        config_entry=entry, suggested_object_id="my_existing_period",
    )

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert calls == ([30.0] if enabled else [])
    assert entry.data == original_data
    assert entry.options[CONF_ENABLED] is enabled
    assert entry.options[CONF_PERIOD_COUNT] == 2
    assert entry.options[CONF_PERIODS] == [
        {**period, PERIOD_USE_STANDARD_TEMPERATURE: False} for period in periods
    ]
    assert entry.options[CONF_STANDARD_TEMPERATURE_ENABLED] is False
    assert entry.options[CONF_STANDARD_TEMPERATURE] == 25.0

    calls.clear()
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert calls == ([30.0] if enabled else [])
    assert entry.data == original_data
    assert entry.options[CONF_ENABLED] is enabled
    assert entry.options[CONF_PERIODS] == [
        {**period, PERIOD_USE_STANDARD_TEMPERATURE: False} for period in periods
    ]
    assert entry.options[CONF_STANDARD_TEMPERATURE_ENABLED] is False
    for old_entity in (old_switch, old_period):
        current = registry.async_get(old_entity.entity_id)
        assert current is not None
        assert current.id == old_entity.id
        assert current.unique_id == old_entity.unique_id
    state = hass.states.get(old_switch.entity_id)
    assert state is not None and state.state == ("on" if enabled else "off")
    new_switch_id = registry.async_get_entity_id(
        "switch", DOMAIN, f"{target}_standard_temperature_enabled",
    )
    assert new_switch_id is not None
    state = hass.states.get(new_switch_id)
    assert state is not None and state.state == "off"
    assert await hass.config_entries.async_unload(entry.entry_id)
