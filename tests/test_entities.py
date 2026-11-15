"""Tests for the compact read-only device presentation."""

import pytest

from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_registry as er
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

TARGET = "climate.heating"


async def test_periods_use_one_read_only_entity_each(
    hass: HomeAssistant,
) -> None:
    """Replace legacy editable controls with one summary sensor per period."""
    hass.states.async_set(
        TARGET,
        "heat",
        {
            "friendly_name": "Heating",
            ATTR_TEMPERATURE: 30.0,
            "min_temp": 10.0,
            "max_temp": 55.0,
            "target_temp_step": 0.5,
            "temperature_unit": "°C",
        },
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=TARGET,
        data={CONF_TARGET_ENTITY: TARGET, CONF_PERIOD_COUNT: 2},
        options={
            CONF_ENABLED: False,
            CONF_PERIOD_COUNT: 2,
            CONF_PERIODS: [
                {
                    PERIOD_ENABLED: True,
                    PERIOD_START: "06:00:00",
                    PERIOD_TEMPERATURE: 30.0,
                },
                {
                    PERIOD_ENABLED: False,
                    PERIOD_START: "22:00:00",
                    PERIOD_TEMPERATURE: 32.0,
                },
            ],
        },
    )
    entry.add_to_hass(hass)

    registry = er.async_get(hass)
    legacy = registry.async_get_or_create(
        "number",
        DOMAIN,
        f"{TARGET}_period_1_temperature",
        config_entry=entry,
    )
    stale_summary = registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{TARGET}_period_3_summary",
        config_entry=entry,
    )

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert registry.async_get(legacy.entity_id) is None
    assert registry.async_get(stale_summary.entity_id) is None
    entries = er.async_entries_for_config_entry(registry, entry.entry_id)
    summaries = {
        registry_entry.unique_id: registry_entry
        for registry_entry in entries
        if registry_entry.unique_id.endswith("_summary")
    }
    assert set(summaries) == {
        f"{TARGET}_period_1_summary",
        f"{TARGET}_period_2_summary",
    }
    diagnostic_timestamps = {
        registry_entry.unique_id
        for registry_entry in entries
        if registry_entry.unique_id.endswith(
            ("_last_temperature_sent", "_last_sync_check")
        )
    }
    assert diagnostic_timestamps == {
        f"{TARGET}_last_temperature_sent",
        f"{TARGET}_last_sync_check",
    }

    first = hass.states.get(summaries[f"{TARGET}_period_1_summary"].entity_id)
    second = hass.states.get(summaries[f"{TARGET}_period_2_summary"].entity_id)
    assert first is not None
    assert first.state == "active"
    assert first.attributes["start"] == "06:00:00"
    assert first.attributes["temperature"] == 30.0
    assert second is not None
    assert second.state == "disabled"
    assert second.attributes["start"] == "22:00:00"
    assert second.attributes["temperature"] == 32.0

    await hass.config_entries.async_unload(entry.entry_id)


async def test_standard_temperature_switch_controls_climate(hass: HomeAssistant) -> None:
    """The new switch is off by default and updates climate and sensor states."""
    hass.states.async_set(TARGET, "heat", {ATTR_TEMPERATURE: 20.0})
    calls: list[float] = []

    async def capture(call: ServiceCall) -> None:
        calls.append(float(call.data[ATTR_TEMPERATURE]))

    hass.services.async_register("climate", "set_temperature", capture)
    entry = MockConfigEntry(domain=DOMAIN, unique_id=TARGET, data={
        CONF_TARGET_ENTITY: TARGET, CONF_PERIOD_COUNT: 1,
        CONF_STANDARD_TEMPERATURE: 23.0,
    })
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    switch_id = registry.async_get_entity_id("switch", DOMAIN, f"{TARGET}_standard_temperature_enabled")
    schedule_id = registry.async_get_entity_id("switch", DOMAIN, f"{TARGET}_schedule_enabled")
    assert switch_id is not None and schedule_id is not None
    for entity_id in (switch_id, schedule_id):
        state = hass.states.get(entity_id)
        assert state is not None and state.state == "off"
    assert calls == []
    await hass.services.async_call("switch", "turn_on", {"entity_id": switch_id}, blocking=True)
    await hass.async_block_till_done()
    assert calls == [23.0]
    assert entry.options[CONF_STANDARD_TEMPERATURE_ENABLED] is True
    switch_state = hass.states.get(switch_id)
    assert switch_state is not None and switch_state.state == "on"
    for key, expected in (("status", "standard_temperature"), ("scheduled_temperature", "20.0"), ("active_period", "1")):
        entity_id = registry.async_get_entity_id("sensor", DOMAIN, f"{TARGET}_{key}")
        assert entity_id is not None
        state = hass.states.get(entity_id)
        assert state is not None and state.state == expected
    await hass.services.async_call("switch", "turn_off", {"entity_id": switch_id}, blocking=True)
    await hass.async_block_till_done()
    assert calls == [23.0]
    assert entry.options[CONF_STANDARD_TEMPERATURE_ENABLED] is False
    await hass.config_entries.async_unload(entry.entry_id)


async def test_standard_temperature_sensor_survives_options_reload(
    hass: HomeAssistant,
) -> None:
    """Show the configured value while disabled and update the same entity after edits."""
    hass.states.async_set(TARGET, "heat", {
        ATTR_TEMPERATURE: 20.0, "temperature_unit": "°C",
    })
    entry = MockConfigEntry(domain=DOMAIN, unique_id=TARGET, data={
        CONF_TARGET_ENTITY: TARGET, CONF_PERIOD_COUNT: 1,
        CONF_STANDARD_TEMPERATURE: 23.0,
    })
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    sensor_id = registry.async_get_entity_id(
        "sensor", DOMAIN, f"{TARGET}_standard_temperature",
    )
    assert sensor_id is not None
    state = hass.states.get(sensor_id)
    assert state is not None and state.state == "23.0"
    assert state.attributes["unit_of_measurement"] == "°C"
    assert state.attributes["device_class"] == "temperature"
    assert entry.options[CONF_ENABLED] is False
    assert entry.options[CONF_STANDARD_TEMPERATURE_ENABLED] is False

    hass.config_entries.async_update_entry(entry, options={
        **entry.options, CONF_STANDARD_TEMPERATURE: 25.5,
    })
    await hass.async_block_till_done()
    assert registry.async_get_entity_id(
        "sensor", DOMAIN, f"{TARGET}_standard_temperature",
    ) == sensor_id
    state = hass.states.get(sensor_id)
    assert state is not None and state.state == "25.5"
    assert entry.options[CONF_ENABLED] is False
    assert entry.options[CONF_STANDARD_TEMPERATURE_ENABLED] is False
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("fallback", [False, True])
@pytest.mark.parametrize("linked,period_enabled", [(False, True), (True, True), (False, False)])
async def test_scheduled_sensor_is_independent_of_control_mode(
    hass: HomeAssistant, enabled: bool, fallback: bool, linked: bool, period_enabled: bool,
) -> None:
    """Display the current period while climate writes still follow the selected control mode."""
    hass.states.async_set(TARGET, "heat", {ATTR_TEMPERATURE: 20.0})
    calls: list[float] = []

    async def capture(call: ServiceCall) -> None:
        calls.append(float(call.data[ATTR_TEMPERATURE]))

    hass.services.async_register("climate", "set_temperature", capture)
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=TARGET,
        data={CONF_TARGET_ENTITY: TARGET, CONF_PERIOD_COUNT: 1},
        options={
            CONF_ENABLED: enabled,
            CONF_STANDARD_TEMPERATURE_ENABLED: fallback,
            CONF_STANDARD_TEMPERATURE: 23.0,
            CONF_PERIODS: [{
                PERIOD_ENABLED: period_enabled,
                PERIOD_START: "00:00:00",
                PERIOD_TEMPERATURE: 26.0,
                PERIOD_USE_STANDARD_TEMPERATURE: linked,
            }],
        },
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    sensor_id = registry.async_get_entity_id("sensor", DOMAIN, f"{TARGET}_scheduled_temperature")
    assert sensor_id is not None
    state = hass.states.get(sensor_id)
    period_temperature = 23.0 if linked else 26.0
    expected_state = str(period_temperature) if period_enabled else "unknown"
    assert state is not None and state.state == expected_state
    if enabled and period_enabled:
        assert calls == [period_temperature]
    elif not enabled and fallback:
        assert calls == [23.0]
    else:
        assert calls == []
    assert await hass.config_entries.async_unload(entry.entry_id)
