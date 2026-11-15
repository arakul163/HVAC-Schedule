"""Config flow for HVAC Schedule."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from homeassistant import config_entries
from homeassistant.components.climate.const import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.climate.const import ClimateEntityFeature
from homeassistant.config_entries import ConfigEntry, ConfigFlowResult
from homeassistant.const import ATTR_SUPPORTED_FEATURES, ATTR_TEMPERATURE
from homeassistant.core import callback
from homeassistant.helpers import selector

from ..const import (
    CONF_ENABLED,
    CONF_STANDARD_TEMPERATURE,
    CONF_STANDARD_TEMPERATURE_ENABLED,
    CONF_PERIOD_COUNT,
    CONF_TARGET_ENTITY,
    DEFAULT_PERIOD_COUNT,
    DOMAIN,
    MAX_PERIOD_COUNT,
    MIN_PERIOD_COUNT,
)
from ..schedule_manager import ScheduleManager
from .schedule_options_flow import ScheduleOptionsFlow
from .typed_selector_module import TypedSelectorModule
from . import flow_schema as vol


_selector_module = cast(TypedSelectorModule, selector)
_EntitySelector = _selector_module.EntitySelector
_NumberSelector = _selector_module.NumberSelector


class ScheduleConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for a climate schedule."""

    VERSION = 1

    _setup_data: dict[str, Any]
    _target_name: str

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Select the climate entity when installing this schedule."""
        errors: dict[str, str] = {}

        if user_input is not None:
            entity_id = user_input[CONF_TARGET_ENTITY]
            state = self.hass.states.get(entity_id)

            if state is None:
                errors["base"] = "entity_not_found"
            elif not (
                int(state.attributes.get(ATTR_SUPPORTED_FEATURES, 0))
                & ClimateEntityFeature.TARGET_TEMPERATURE
            ):
                errors["base"] = "target_temperature_not_supported"
            else:
                await self.async_set_unique_id(entity_id)
                self._abort_if_unique_id_configured()

                period_count = int(user_input[CONF_PERIOD_COUNT])
                self._setup_data = {
                    CONF_TARGET_ENTITY: entity_id,
                    CONF_PERIOD_COUNT: period_count,
                }
                self._target_name = state.name
                return await self.async_step_standard_temperature()

        schema = vol.Schema(
            {
                vol.Required(CONF_TARGET_ENTITY): _EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=CLIMATE_DOMAIN,
                        multiple=False,
                    )
                ),
                vol.Required(
                    CONF_PERIOD_COUNT, default=DEFAULT_PERIOD_COUNT
                ): _NumberSelector(
                    selector.NumberSelectorConfig(
                        min=MIN_PERIOD_COUNT,
                        max=MAX_PERIOD_COUNT,
                        step=1,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_standard_temperature(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Choose the standard temperature using the selected climate limits."""
        state = self.hass.states.get(self._setup_data[CONF_TARGET_ENTITY])
        attributes: Mapping[str, Any] = state.attributes if state is not None else {}
        minimum = float(attributes.get("min_temp", 7.0))
        maximum = float(attributes.get("max_temp", 35.0))
        step = float(attributes.get("target_temp_step", 0.5))
        if user_input is not None:
            temperature = min(max(float(user_input[CONF_STANDARD_TEMPERATURE]), minimum), maximum)
            if step > 0:
                temperature = round(minimum + round((temperature - minimum) / step) * step, 3)
            return self.async_create_entry(
                title=self._target_name,
                data={**self._setup_data, CONF_STANDARD_TEMPERATURE: temperature},
                options={CONF_ENABLED: False, CONF_STANDARD_TEMPERATURE_ENABLED: False},
            )
        default = attributes.get(ATTR_TEMPERATURE)
        if default is None:
            default = (minimum + maximum) / 2
        return self.async_show_form(
            step_id="standard_temperature",
            data_schema=vol.Schema({
                vol.Required(CONF_STANDARD_TEMPERATURE, default=min(max(float(default), minimum), maximum)):
                    _NumberSelector(selector.NumberSelectorConfig(
                        min=minimum, max=maximum, step=step,
                        mode=selector.NumberSelectorMode.SLIDER,
                        unit_of_measurement=str(attributes.get(
                            "temperature_unit", self.hass.config.units.temperature_unit
                        )),
                    )),
            }),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry[ScheduleManager]) -> ScheduleOptionsFlow:
        """Return the period reconfiguration flow."""
        del config_entry
        return ScheduleOptionsFlow()
