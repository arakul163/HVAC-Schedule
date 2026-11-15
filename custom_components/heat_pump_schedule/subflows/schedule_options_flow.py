"""Options flow for HVAC Schedule."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import time
from typing import Any, cast

from homeassistant.config_entries import ConfigFlowResult, OptionsFlow
from homeassistant.helpers import selector
from homeassistant.helpers.translation import async_get_translations

from ..const import (
    CONF_ENABLED,
    CONF_STANDARD_TEMPERATURE,
    CONF_STANDARD_TEMPERATURE_ENABLED,
    CONF_PERIOD_COUNT,
    CONF_PERIODS,
    CONF_TARGET_ENTITY,
    DEFAULT_PERIOD_COUNT,
    DOMAIN,
    MAX_PERIOD_COUNT,
    MIN_PERIOD_COUNT,
    PERIOD_ENABLED,
    PERIOD_START,
    PERIOD_TEMPERATURE,
    PERIOD_USE_STANDARD_TEMPERATURE,
)
from ..schedule import parse_time
from ..schedule_manager import ScheduleManager
from .typed_selector_module import TypedSelectorModule
from . import flow_schema as vol


_selector_module = cast(TypedSelectorModule, selector)
_NumberSelector = _selector_module.NumberSelector
_BooleanSelector = _selector_module.BooleanSelector
_TimeSelector = _selector_module.TimeSelector


def _periods_from_storage(value: object) -> list[dict[str, Any]]:
    """Return typed period mappings from untyped config entry storage."""
    if not isinstance(value, list):
        return []
    items = cast(list[object], value)
    return [cast(dict[str, Any], item) for item in items if isinstance(item, dict)]


class ScheduleOptionsFlow(OptionsFlow):
    """Reconfigure schedule periods while keeping the target immutable."""

    def __init__(self) -> None:
        """Initialize the options wizard."""
        self._period_count = DEFAULT_PERIOD_COUNT
        self._period_index = 0
        self._periods: list[dict[str, Any]] = []
        self._minimum = 7.0
        self._maximum = 35.0
        self._step = 0.5
        self._unit = "°C"
        self._standard_temperature = 21.0

    async def async_step_init(self, _user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Load the current schedule and show its period overview."""
        self._period_count = int(
            self.config_entry.options.get(
                CONF_PERIOD_COUNT,
                self.config_entry.data[CONF_PERIOD_COUNT],
            )
        )
        self._prepare_periods()
        self._standard_temperature = self._align_temperature(float(
            self.config_entry.options.get(CONF_STANDARD_TEMPERATURE,
                self.config_entry.data.get(CONF_STANDARD_TEMPERATURE,
                    (self._minimum + self._maximum) / 2))
        ))
        return await self.async_step_overview()

    async def async_step_overview(self, _user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Show every period as a single selectable summary row."""
        return self.async_show_menu(
            step_id="overview",
            menu_options=await self._async_menu_options(),
            description_placeholders={"target": self._target_label()},
        )

    async def async_step_standard_temperature(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Configure the constant temperature used outside schedule control."""
        if user_input is not None:
            self._standard_temperature = self._align_temperature(
                float(user_input[CONF_STANDARD_TEMPERATURE])
            )
            return await self.async_step_overview()
        return self.async_show_form(
            step_id="standard_temperature",
            data_schema=vol.Schema({
                vol.Required(CONF_STANDARD_TEMPERATURE, default=self._standard_temperature):
                    _NumberSelector(selector.NumberSelectorConfig(
                        min=self._minimum, max=self._maximum, step=self._step,
                        mode=selector.NumberSelectorMode.SLIDER,
                        unit_of_measurement=self._unit,
                    )),
            }),
        )

    async def async_step_period_count(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Change the number of periods while preserving existing values."""
        if user_input is not None:
            source = [dict(period) for period in self._periods]
            self._period_count = int(user_input[CONF_PERIOD_COUNT])
            self._prepare_periods(source)
            return await self.async_step_overview()

        return self.async_show_form(
            step_id="period_count",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_PERIOD_COUNT, default=self._period_count
                    ): _NumberSelector(
                        selector.NumberSelectorConfig(
                            min=MIN_PERIOD_COUNT,
                            max=MAX_PERIOD_COUNT,
                            step=1,
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    )
                }
            ),
            description_placeholders={"target": self._target_label()},
        )

    async def async_step_period_1(self, _user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Open period 1."""
        return await self._async_open_period(0)

    async def async_step_period_2(self, _user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Open period 2."""
        return await self._async_open_period(1)

    async def async_step_period_3(self, _user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Open period 3."""
        return await self._async_open_period(2)

    async def async_step_period_4(self, _user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Open period 4."""
        return await self._async_open_period(3)

    async def async_step_period_5(self, _user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Open period 5."""
        return await self._async_open_period(4)

    async def async_step_period_6(self, _user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Open period 6."""
        return await self._async_open_period(5)

    async def async_step_period_7(self, _user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Open period 7."""
        return await self._async_open_period(6)

    async def async_step_period_8(self, _user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Open period 8."""
        return await self._async_open_period(7)

    async def async_step_period_9(self, _user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Open period 9."""
        return await self._async_open_period(8)

    async def async_step_period_10(self, _user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Open period 10."""
        return await self._async_open_period(9)

    async def async_step_period_11(self, _user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Open period 11."""
        return await self._async_open_period(10)

    async def async_step_period_12(self, _user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Open period 12."""
        return await self._async_open_period(11)

    async def _async_open_period(self, index: int) -> ConfigFlowResult:
        """Open the editor for one selected period."""
        self._period_index = index
        return await self.async_step_period()

    async def async_step_period(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Edit one period and return to the period overview."""
        period = self._periods[self._period_index]

        if user_input is not None:
            raw_start = user_input[PERIOD_START]
            start = (
                raw_start.replace(microsecond=0).isoformat()
                if isinstance(raw_start, time)
                else parse_time(str(raw_start)).replace(microsecond=0).isoformat()
            )
            use_standard = bool(user_input.get(PERIOD_USE_STANDARD_TEMPERATURE, False))
            temperature = float(period[PERIOD_TEMPERATURE])
            if not use_standard:
                temperature = float(user_input.get(PERIOD_TEMPERATURE, temperature))
            period.update(
                {
                    PERIOD_ENABLED: bool(user_input[PERIOD_ENABLED]),
                    PERIOD_START: start,
                    PERIOD_USE_STANDARD_TEMPERATURE: use_standard,
                    PERIOD_TEMPERATURE: self._align_temperature(temperature),
                }
            )
            return await self.async_step_overview()

        return self.async_show_form(
            step_id="period",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        PERIOD_ENABLED,
                        default=bool(period[PERIOD_ENABLED]),
                    ): _BooleanSelector(),
                    vol.Required(
                        PERIOD_START,
                        default=str(period[PERIOD_START]),
                    ): _TimeSelector(),
                    vol.Required(
                        PERIOD_USE_STANDARD_TEMPERATURE,
                        default=bool(period.get(PERIOD_USE_STANDARD_TEMPERATURE, False)),
                    ): _BooleanSelector(),
                    vol.optional_when(
                        PERIOD_TEMPERATURE,
                        default=float(period[PERIOD_TEMPERATURE]),
                        controlling_field=PERIOD_USE_STANDARD_TEMPERATURE,
                        value=False,
                    ): _NumberSelector(
                        selector.NumberSelectorConfig(
                            min=self._minimum,
                            max=self._maximum,
                            step=self._step,
                            mode=selector.NumberSelectorMode.SLIDER,
                            unit_of_measurement=self._unit,
                        )
                    ),
                }
            ),
            description_placeholders={
                "number": str(self._period_index + 1),
            },
        )

    async def async_step_save(self, _user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Save all period changes."""
        return self.async_create_entry(
            title="",
            data={
                CONF_ENABLED: bool(self.config_entry.options.get(CONF_ENABLED, False)),
                CONF_STANDARD_TEMPERATURE: self._standard_temperature,
                CONF_STANDARD_TEMPERATURE_ENABLED: bool(self.config_entry.options.get(CONF_STANDARD_TEMPERATURE_ENABLED, False)),
                CONF_PERIOD_COUNT: self._period_count,
                CONF_PERIODS: self._periods,
            },
        )

    def _prepare_periods(self, source: list[dict[str, Any]] | None = None) -> None:
        """Load existing values and create defaults for newly added periods."""
        if source is None:
            manager = cast(
                ScheduleManager | None,
                getattr(self.config_entry, "runtime_data", None),
            )
            if manager is not None:
                source = [dict(period) for period in manager.periods]
                self._minimum = float(manager.min_temperature)
                self._maximum = float(manager.max_temperature)
                self._step = float(manager.temperature_step)
                self._unit = str(manager.temperature_unit)
            else:
                source = _periods_from_storage(
                    self.config_entry.options.get(CONF_PERIODS, [])
                )
                target = self.hass.states.get(
                    self.config_entry.data[CONF_TARGET_ENTITY]
                )
                attributes: Mapping[str, Any] = (
                    target.attributes if target is not None else {}
                )
                self._minimum = float(attributes.get("min_temp", self._minimum))
                self._maximum = float(attributes.get("max_temp", self._maximum))
                self._step = float(attributes.get("target_temp_step", self._step))
                self._unit = str(attributes.get("temperature_unit", self._unit))

        default_temperature = (
            float(source[0][PERIOD_TEMPERATURE])
            if source
            else (self._minimum + self._maximum) / 2
        )

        self._periods = []
        for index in range(self._period_count):
            seconds = int(index * 86400 / self._period_count)
            default_start = time(
                hour=seconds // 3600,
                minute=(seconds % 3600) // 60,
            ).isoformat()
            raw = source[index] if index < len(source) else {}
            try:
                start = (
                    parse_time(str(raw.get(PERIOD_START, default_start)))
                    .replace(microsecond=0)
                    .isoformat()
                )
            except ValueError:
                start = default_start
            try:
                temperature = float(raw.get(PERIOD_TEMPERATURE, default_temperature))
            except (TypeError, ValueError):
                temperature = default_temperature

            self._periods.append(
                {
                    PERIOD_ENABLED: bool(raw.get(PERIOD_ENABLED, index == 0)),
                    PERIOD_START: start,
                    PERIOD_USE_STANDARD_TEMPERATURE: bool(raw.get(PERIOD_USE_STANDARD_TEMPERATURE, False)),
                    PERIOD_TEMPERATURE: self._align_temperature(temperature),
                }
            )

    async def _async_menu_options(self) -> dict[str, str]:
        """Build localized labels containing each period's current values."""
        option_translations = await async_get_translations(
            self.hass,
            self.hass.config.language,
            "options",
            integrations={DOMAIN},
        )
        entity_translations = await async_get_translations(
            self.hass,
            self.hass.config.language,
            "entity",
            integrations={DOMAIN},
        )
        prefix = f"component.{DOMAIN}.options.step.overview.menu_options"
        state_prefix = f"component.{DOMAIN}.entity.sensor.schedule_status.state"
        menu_options: dict[str, str] = {}

        for index, period in enumerate(self._periods):
            state = "active" if period[PERIOD_ENABLED] else "disabled"
            template = option_translations[f"{prefix}.period_{index + 1}"]
            temperature = float(period[PERIOD_TEMPERATURE])
            if period.get(PERIOD_USE_STANDARD_TEMPERATURE, False):
                temperature = self._standard_temperature

            temperature_label = self._format_temperature(temperature)
            if period.get(PERIOD_USE_STANDARD_TEMPERATURE, False):
                temperature_label = (
                    f"{entity_translations[f'{state_prefix}.standard_temperature']}: "
                    f"{temperature_label}"
                )
            menu_options[f"period_{index + 1}"] = template.format(
                number=index + 1,
                start=str(period[PERIOD_START])[:5],
                temperature=temperature_label,
                unit=self._unit,
                state=entity_translations[f"{state_prefix}.{state}"],
            )

        menu_options["period_count"] = option_translations[
            f"{prefix}.period_count"
        ].format(count=self._period_count)
        menu_options["standard_temperature"] = option_translations[
            f"{prefix}.standard_temperature"
        ].format(temperature=self._format_temperature(self._standard_temperature), unit=self._unit)
        menu_options["save"] = option_translations[f"{prefix}.save"]
        return menu_options

    @staticmethod
    def _format_temperature(value: float) -> str:
        """Format a temperature without unnecessary trailing zeroes."""
        return f"{value:.3f}".rstrip("0").rstrip(".")

    def _align_temperature(self, value: float) -> float:
        """Clamp a temperature to the selected climate's limits and step."""
        clamped = min(max(value, self._minimum), self._maximum)
        if self._step <= 0:
            return clamped
        steps = round((clamped - self._minimum) / self._step)
        return round(self._minimum + steps * self._step, 3)

    def _target_label(self) -> str:
        """Return a read-only label for the immutable target entity."""
        entity_id = self.config_entry.data[CONF_TARGET_ENTITY]
        state = self.hass.states.get(entity_id)
        return f"{state.name} ({entity_id})" if state is not None else entity_id
