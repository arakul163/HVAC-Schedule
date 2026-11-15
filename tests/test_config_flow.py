"""Tests for installation and period reconfiguration flows."""

from collections.abc import Mapping
from typing import Any, Protocol, cast

import pytest
from unittest.mock import patch

from homeassistant.components.climate.const import ClimateEntityFeature
from homeassistant.config_entries import SOURCE_USER, ConfigFlowResult
from homeassistant.const import ATTR_SUPPORTED_FEATURES, ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
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


class _FlowManager(Protocol):
    """Typed view of Home Assistant's incompletely annotated flow manager."""

    async def async_configure(
        self,
        flow_id: str,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult: ...


def _flow_manager(manager: object) -> _FlowManager:
    """Restore the concrete async_configure signature for strict checking."""
    return cast(_FlowManager, manager)


def _set_target(hass: HomeAssistant, *, supported: bool = True) -> None:
    """Create a selectable climate entity."""
    features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        if supported
        else ClimateEntityFeature(0)
    )
    hass.states.async_set(
        TARGET,
        "heat",
        {
            "friendly_name": "Heating",
            ATTR_SUPPORTED_FEATURES: int(features),
            ATTR_TEMPERATURE: 30.0,
            "min_temp": 10.0,
            "max_temp": 55.0,
            "target_temp_step": 0.5,
            "temperature_unit": "°C",
        },
    )


def _schema_keys(result: ConfigFlowResult) -> set[str]:
    """Extract field names from a flow result schema."""
    schema = result.get("data_schema")
    assert schema is not None
    return {str(getattr(marker, "schema", marker)) for marker in schema.schema}


def _description_placeholders(result: ConfigFlowResult) -> Mapping[str, str]:
    """Return the required description placeholders from a flow result."""
    placeholders = result.get("description_placeholders")
    assert placeholders is not None
    return placeholders


def _menu_options(result: ConfigFlowResult) -> Mapping[str, str]:
    """Return subscriptable menu options from a flow result."""
    options = result.get("menu_options")
    assert isinstance(options, Mapping)
    return cast(Mapping[str, str], options)


async def test_user_flow_creates_entry(hass: HomeAssistant) -> None:
    """Installation stores the selected immutable target and period count."""
    _set_target(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )
    assert result.get("type") is FlowResultType.FORM
    assert result.get("step_id") == "user"

    with patch(
        "custom_components.heat_pump_schedule.async_setup_entry",
        return_value=True,
    ):
        result = await _flow_manager(hass.config_entries.flow).async_configure(
            result["flow_id"],
            {
                CONF_TARGET_ENTITY: TARGET,
                CONF_PERIOD_COUNT: 6,
            },
        )
        assert result.get("step_id") == "standard_temperature"
        assert _schema_keys(result) == {CONF_STANDARD_TEMPERATURE}
        result = await _flow_manager(hass.config_entries.flow).async_configure(
            result["flow_id"], {CONF_STANDARD_TEMPERATURE: 28.3},
        )
        await hass.async_block_till_done()

    assert result.get("type") is FlowResultType.CREATE_ENTRY
    assert result.get("title") == "Heating"
    assert result.get("data") == {
        CONF_TARGET_ENTITY: TARGET,
        CONF_PERIOD_COUNT: 6,
        CONF_STANDARD_TEMPERATURE: 28.5,
    }
    created_entry = result.get("result")
    assert created_entry is not None
    assert created_entry.unique_id == TARGET
    assert created_entry.options == {CONF_ENABLED: False, CONF_STANDARD_TEMPERATURE_ENABLED: False}


async def test_user_flow_rejects_missing_entity(hass: HomeAssistant) -> None:
    """An entity that is not in the state machine cannot be selected."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )
    result = await _flow_manager(hass.config_entries.flow).async_configure(
        result["flow_id"],
        {
            CONF_TARGET_ENTITY: TARGET,
            CONF_PERIOD_COUNT: 6,
        },
    )

    assert result.get("type") is FlowResultType.FORM
    assert result.get("errors") == {"base": "entity_not_found"}


async def test_user_flow_rejects_unsupported_climate(
    hass: HomeAssistant,
) -> None:
    """The target must support a single target temperature."""
    _set_target(hass, supported=False)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )
    result = await _flow_manager(hass.config_entries.flow).async_configure(
        result["flow_id"],
        {
            CONF_TARGET_ENTITY: TARGET,
            CONF_PERIOD_COUNT: 6,
        },
    )

    assert result.get("type") is FlowResultType.FORM
    assert result.get("errors") == {"base": "target_temperature_not_supported"}


async def test_user_flow_rejects_duplicate_target(
    hass: HomeAssistant,
) -> None:
    """Only one schedule can be installed for a climate entity."""
    _set_target(hass)
    MockConfigEntry(
        domain=DOMAIN,
        unique_id=TARGET,
        data={CONF_TARGET_ENTITY: TARGET, CONF_PERIOD_COUNT: 6},
    ).add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )
    result = await _flow_manager(hass.config_entries.flow).async_configure(
        result["flow_id"],
        {
            CONF_TARGET_ENTITY: TARGET,
            CONF_PERIOD_COUNT: 6,
        },
    )

    assert result.get("type") is FlowResultType.ABORT
    assert result.get("reason") == "already_configured"


async def test_options_flow_edits_periods_but_not_target(
    hass: HomeAssistant,
) -> None:
    """Configure edits every period while keeping config entry data intact."""
    _set_target(hass)
    original_data = {CONF_TARGET_ENTITY: TARGET, CONF_PERIOD_COUNT: 2}
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=TARGET,
        data=original_data,
        options={
            CONF_ENABLED: True,
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

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result.get("type") is FlowResultType.MENU
    assert result.get("step_id") == "overview"
    assert TARGET in _description_placeholders(result)["target"]
    assert _menu_options(result) == {
        "period_1": "Period 1 · 06:00 — 30 °C (Active)",
        "period_2": "Period 2 · 22:00 — 32 °C (Active)",
        "period_count": "Number of periods: 2",
        "save": "Save changes",
        "standard_temperature": "Standard temperature: 32.5 °C",
    }

    result = await _flow_manager(hass.config_entries.options).async_configure(
        result["flow_id"],
        {"next_step_id": "period_count"},
    )
    assert result.get("type") is FlowResultType.FORM
    assert result.get("step_id") == "period_count"
    assert _schema_keys(result) == {CONF_PERIOD_COUNT}
    assert CONF_TARGET_ENTITY not in _schema_keys(result)

    result = await _flow_manager(hass.config_entries.options).async_configure(
        result["flow_id"],
        {CONF_PERIOD_COUNT: 2},
    )
    assert result.get("type") is FlowResultType.MENU

    result = await _flow_manager(hass.config_entries.options).async_configure(
        result["flow_id"],
        {"next_step_id": "period_1"},
    )
    assert result.get("type") is FlowResultType.FORM
    assert result.get("step_id") == "period"
    assert _schema_keys(result) == {
        PERIOD_ENABLED,
        PERIOD_START,
        PERIOD_TEMPERATURE,
        PERIOD_USE_STANDARD_TEMPERATURE,
    }

    result = await _flow_manager(hass.config_entries.options).async_configure(
        result["flow_id"],
        {
            PERIOD_ENABLED: True,
            PERIOD_START: "07:00:00",
            PERIOD_TEMPERATURE: 31.3,
        },
    )
    assert result.get("type") is FlowResultType.MENU
    assert _menu_options(result)["period_1"] == ("Period 1 · 07:00 — 31.5 °C (Active)")

    result = await _flow_manager(hass.config_entries.options).async_configure(
        result["flow_id"],
        {"next_step_id": "period_2"},
    )
    assert result.get("type") is FlowResultType.FORM
    assert _description_placeholders(result) == {"number": "2"}

    result = await _flow_manager(hass.config_entries.options).async_configure(
        result["flow_id"],
        {
            PERIOD_ENABLED: False,
            PERIOD_START: "23:00:00",
            PERIOD_TEMPERATURE: 33.0,
        },
    )
    assert result.get("type") is FlowResultType.MENU
    assert _menu_options(result)["period_2"] == ("Period 2 · 23:00 — 33 °C (Disabled)")

    result = await _flow_manager(hass.config_entries.options).async_configure(
        result["flow_id"], {"next_step_id": "standard_temperature"},
    )
    assert _schema_keys(result) == {CONF_STANDARD_TEMPERATURE}
    result = await _flow_manager(hass.config_entries.options).async_configure(
        result["flow_id"], {CONF_STANDARD_TEMPERATURE: 27.3},
    )
    assert _menu_options(result)["standard_temperature"] == "Standard temperature: 27.5 °C"

    result = await _flow_manager(hass.config_entries.options).async_configure(
        result["flow_id"],
        {"next_step_id": "save"},
    )

    assert result.get("type") is FlowResultType.CREATE_ENTRY
    assert entry.data == original_data
    assert entry.options == {
        CONF_ENABLED: True,
        CONF_STANDARD_TEMPERATURE_ENABLED: False,
        CONF_STANDARD_TEMPERATURE: 27.5,
        CONF_PERIOD_COUNT: 2,
        CONF_PERIODS: [
            {
                PERIOD_USE_STANDARD_TEMPERATURE: False,
                PERIOD_ENABLED: True,
                PERIOD_START: "07:00:00",
                PERIOD_TEMPERATURE: 31.5,
            },
            {
                PERIOD_USE_STANDARD_TEMPERATURE: False,
                PERIOD_ENABLED: False,
                PERIOD_START: "23:00:00",
                PERIOD_TEMPERATURE: 33.0,
            },
        ],
    }


@pytest.mark.parametrize("submitted_temperature", [None, 40.0])
async def test_period_can_follow_standard_temperature(
    hass: HomeAssistant, submitted_temperature: float | None,
) -> None:
    """Link a period without entering a temperature and retain its custom value."""
    _set_target(hass)
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=TARGET,
        data={CONF_TARGET_ENTITY: TARGET, CONF_PERIOD_COUNT: 1},
        options={
            CONF_STANDARD_TEMPERATURE: 26.0,
            CONF_PERIODS: [{
                PERIOD_ENABLED: True, PERIOD_START: "06:00:00",
                PERIOD_TEMPERATURE: 31.0,
            }],
        },
    )
    entry.add_to_hass(hass)
    flow = _flow_manager(hass.config_entries.options)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await flow.async_configure(result["flow_id"], {"next_step_id": "period_1"})
    period_input: dict[str, Any] = {
        PERIOD_ENABLED: True, PERIOD_START: "06:00:00",
        PERIOD_USE_STANDARD_TEMPERATURE: True,
    }
    if submitted_temperature is not None:
        period_input[PERIOD_TEMPERATURE] = submitted_temperature
    result = await flow.async_configure(result["flow_id"], period_input)
    assert "Standard temperature: 26 °C" in _menu_options(result)["period_1"]
    result = await flow.async_configure(result["flow_id"], {"next_step_id": "standard_temperature"})
    result = await flow.async_configure(result["flow_id"], {CONF_STANDARD_TEMPERATURE: 28.0})
    assert "Standard temperature: 28 °C" in _menu_options(result)["period_1"]
    result = await flow.async_configure(result["flow_id"], {"next_step_id": "save"})
    assert result.get("type") is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_PERIODS][0][PERIOD_USE_STANDARD_TEMPERATURE] is True
    assert entry.options[CONF_PERIODS][0][PERIOD_TEMPERATURE] == 31.0

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert "Standard temperature: 28 °C" in _menu_options(result)["period_1"]
    result = await flow.async_configure(result["flow_id"], {"next_step_id": "period_count"})
    result = await flow.async_configure(result["flow_id"], {CONF_PERIOD_COUNT: 2})
    assert "Standard temperature: 28 °C" in _menu_options(result)["period_1"]
    result = await flow.async_configure(result["flow_id"], {"next_step_id": "period_1"})
    result = await flow.async_configure(result["flow_id"], {
        PERIOD_ENABLED: True, PERIOD_START: "06:00:00",
        PERIOD_USE_STANDARD_TEMPERATURE: False,
    })
    assert _menu_options(result)["period_1"] == "Period 1 · 06:00 — 31 °C (Active)"
    result = await flow.async_configure(result["flow_id"], {"next_step_id": "save"})
    assert entry.options[CONF_PERIODS][0][PERIOD_USE_STANDARD_TEMPERATURE] is False
