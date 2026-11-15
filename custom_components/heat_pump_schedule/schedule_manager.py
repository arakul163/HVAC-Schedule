"""Runtime manager for one installed HVAC Schedule."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, time
from typing import Any, cast

from homeassistant.components.climate.const import (
    DOMAIN as CLIMATE_DOMAIN,
)
from homeassistant.components.climate.const import (
    SERVICE_SET_TEMPERATURE,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt as dt_util

from .const import (
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
from .schedule import active_period_index, parse_time

_LOGGER = logging.getLogger(__name__)


class ScheduleManager:
    """Own schedule state, persistence, timing, and climate writes."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry[ScheduleManager]
    ) -> None:
        """Initialize the manager."""
        self.hass = hass
        self.entry = entry
        self.target_entity_id: str = entry.data[CONF_TARGET_ENTITY]
        self.period_count: int = int(
            entry.options.get(CONF_PERIOD_COUNT, entry.data[CONF_PERIOD_COUNT])
        )
        self._listeners: set[Callable[[], None]] = set()
        self._unsub_timer: Callable[[], None] | None = None
        self._apply_lock = asyncio.Lock()
        self.last_error: str | None = None
        self.last_applied: datetime | None = None
        self.last_applied_temperature: float | None = None
        self.last_temperature_sent: datetime | None = None
        self.last_sync_check: datetime | None = None
        self._last_snapshot: tuple[Any, ...] | None = None

        target_state = hass.states.get(self.target_entity_id)
        attributes: Mapping[str, Any] = (
            target_state.attributes if target_state is not None else {}
        )
        self.min_temperature = float(attributes.get("min_temp", 7.0))
        self.max_temperature = float(attributes.get("max_temp", 35.0))
        self.temperature_step = float(attributes.get("target_temp_step", 0.5))
        self.temperature_unit = str(
            attributes.get(
                "temperature_unit",
                hass.config.units.temperature_unit or UnitOfTemperature.CELSIUS,
            )
        )

        current_target = attributes.get(ATTR_TEMPERATURE)
        if current_target is None:
            default_temperature = (self.min_temperature + self.max_temperature) / 2
        else:
            default_temperature = float(current_target)
        default_temperature = self._clamp_temperature(default_temperature)

        self.enabled = bool(entry.options.get(CONF_ENABLED, False))
        self.standard_temperature_enabled = bool(
            entry.options.get(CONF_STANDARD_TEMPERATURE_ENABLED, False)
        )
        self.standard_temperature = self._clamp_temperature(float(
            entry.options.get(CONF_STANDARD_TEMPERATURE,
                              entry.data.get(CONF_STANDARD_TEMPERATURE, default_temperature))
        ))
        stored_periods = entry.options.get(CONF_PERIODS)
        self.periods = self._normalize_periods(stored_periods, default_temperature)

    @property
    def device_info(self) -> DeviceInfo:
        """Return the virtual device for this installed schedule."""
        state = self.hass.states.get(self.target_entity_id)
        target_name = state.name if state is not None else self.target_entity_id
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            translation_key="schedule",
            translation_placeholders={"target": target_name},
            manufacturer="Home Assistant Custom",
            model="HVAC Schedule",
        )

    async def async_setup(self) -> None:
        """Start the minute boundary tracker and persist normalized defaults."""
        self._persist()
        self._unsub_timer = async_track_time_change(
            self.hass,
            self._handle_minute,
            second=0,
        )
        self._notify_if_changed(force=True)
        self.hass.async_create_task(self.async_apply())

    async def async_unload(self) -> None:
        """Stop tracking time for this schedule."""
        if self._unsub_timer is not None:
            self._unsub_timer()
            self._unsub_timer = None
        self._listeners.clear()

    @callback
    def _handle_minute(self, now: datetime) -> None:
        """Apply the schedule at each local minute boundary."""
        self.hass.async_create_task(self.async_apply(now))

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Subscribe an entity to manager updates."""
        self._listeners.add(listener)

        @callback
        def remove_listener() -> None:
            self._listeners.discard(listener)

        return remove_listener

    def active_period_index(self, now: datetime | None = None) -> int | None:
        """Return the current scheduled period regardless of the control mode."""
        local_now = now or dt_util.now()
        return active_period_index(self.periods, local_now.time())

    def desired_temperature(self, now: datetime | None = None) -> float | None:
        """Return the temperature to apply for the current control mode."""
        if self.using_standard_temperature:
            return self.standard_temperature
        return self.scheduled_temperature(now)

    def scheduled_temperature(self, now: datetime | None = None) -> float | None:
        """Return the current period temperature independently of control switches."""
        index = self.active_period_index(now)
        if index is None:
            return None
        return self.period_temperature(index)

    @property
    def using_standard_temperature(self) -> bool:
        """Return whether the constant temperature mode is active."""
        return not self.enabled and self.standard_temperature_enabled

    @property
    def status(self) -> str:
        """Return a compact diagnostic status."""
        if not self.enabled and not self.standard_temperature_enabled:
            return "disabled"
        if not self.using_standard_temperature and self.active_period_index() is None:
            return "no_enabled_periods"
        state = self.hass.states.get(self.target_entity_id)
        if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return "target_unavailable"
        if self.last_error is not None:
            return "error"
        return "standard_temperature" if self.using_standard_temperature else "active"

    async def async_set_enabled(self, enabled: bool) -> None:
        """Enable or disable automatic application."""
        self.enabled = enabled
        self.last_error = None
        self._persist()
        self._notify_if_changed(force=True)
        await self.async_apply()

    async def async_set_standard_temperature_enabled(self, enabled: bool) -> None:
        """Toggle constant temperature control when the schedule is disabled."""
        self.standard_temperature_enabled = enabled
        self.last_error = None
        self._persist()
        self._notify_if_changed(force=True)
        await self.async_apply()

    async def async_set_period_enabled(self, index: int, enabled: bool) -> None:
        """Enable or disable one period."""
        self.periods[index][PERIOD_ENABLED] = enabled
        await self._async_period_changed()

    async def async_set_period_start(self, index: int, value: time) -> None:
        """Set one period's local start time."""
        self.periods[index][PERIOD_START] = value.replace(microsecond=0).isoformat()
        await self._async_period_changed()

    async def async_set_period_temperature(self, index: int, value: float) -> None:
        """Set one period's target temperature."""
        self.periods[index][PERIOD_TEMPERATURE] = self._clamp_temperature(value)
        await self._async_period_changed()

    async def _async_period_changed(self) -> None:
        """Persist a schedule edit and immediately re-evaluate it."""
        self.last_error = None
        self._persist()
        self._notify_if_changed(force=True)
        await self.async_apply()

    async def async_apply(
        self, now: datetime | None = None, *, force: bool = False
    ) -> None:
        """Apply the currently active period to the target climate."""
        async with self._apply_lock:
            if not self.enabled and not self.standard_temperature_enabled and not force:
                self._notify_if_changed()
                return

            self.last_sync_check = datetime.now(UTC)
            desired = self.desired_temperature(now)
            if desired is None:
                self._notify_if_changed()
                return

            target_state = self.hass.states.get(self.target_entity_id)
            if target_state is None or target_state.state in (
                STATE_UNKNOWN,
                STATE_UNAVAILABLE,
            ):
                self.last_error = "target_unavailable"
                self._notify_if_changed()
                return

            current_target = target_state.attributes.get(ATTR_TEMPERATURE)
            if (
                not force
                and current_target is not None
                and abs(float(current_target) - desired) < 0.05
            ):
                self.last_error = None
                self._notify_if_changed()
                return

            try:
                self.last_temperature_sent = datetime.now(UTC)
                await self.hass.services.async_call(
                    CLIMATE_DOMAIN,
                    SERVICE_SET_TEMPERATURE,
                    {
                        ATTR_ENTITY_ID: self.target_entity_id,
                        ATTR_TEMPERATURE: desired,
                    },
                    blocking=True,
                )
            except HomeAssistantError as err:
                self.last_error = str(err)
                _LOGGER.warning(
                    "Could not set %s to %s: %s",
                    self.target_entity_id,
                    desired,
                    err,
                )
            else:
                self.last_error = None
                self.last_applied = datetime.now(UTC)
                self.last_applied_temperature = desired

            self._notify_if_changed()

    def period_start(self, index: int) -> time:
        """Return a period start time."""
        return parse_time(str(self.periods[index][PERIOD_START]))

    def period_temperature(self, index: int) -> float:
        """Return a period target temperature."""
        if self.period_uses_standard_temperature(index):
            return self.standard_temperature
        return float(self.periods[index][PERIOD_TEMPERATURE])

    def period_uses_standard_temperature(self, index: int) -> bool:
        """Return whether a period follows the configured standard temperature."""
        return bool(self.periods[index].get(PERIOD_USE_STANDARD_TEMPERATURE, False))

    def period_enabled(self, index: int) -> bool:
        """Return whether a period is enabled."""
        return bool(self.periods[index][PERIOD_ENABLED])

    def _normalize_periods(
        self, stored_periods: object, default_temperature: float
    ) -> list[dict[str, Any]]:
        """Validate stored periods and fill missing entries."""
        source = (
            cast(list[object], stored_periods)
            if isinstance(stored_periods, list)
            else []
        )
        normalized: list[dict[str, Any]] = []

        for index in range(self.period_count):
            default_seconds = int(index * 86400 / self.period_count)
            default_start = time(
                hour=default_seconds // 3600,
                minute=(default_seconds % 3600) // 60,
            ).isoformat()
            candidate = source[index] if index < len(source) else None
            raw = cast(dict[str, Any], candidate) if isinstance(candidate, dict) else {}

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

            normalized.append(
                {
                    PERIOD_ENABLED: bool(raw.get(PERIOD_ENABLED, index == 0)),
                    PERIOD_START: start,
                    PERIOD_USE_STANDARD_TEMPERATURE: bool(raw.get(PERIOD_USE_STANDARD_TEMPERATURE, False)),
                    PERIOD_TEMPERATURE: self._clamp_temperature(temperature),
                }
            )

        return normalized

    def _clamp_temperature(self, value: float) -> float:
        """Clamp and align a temperature to the target climate capabilities."""
        clamped = min(max(float(value), self.min_temperature), self.max_temperature)
        if self.temperature_step <= 0:
            return clamped
        steps = round((clamped - self.min_temperature) / self.temperature_step)
        return round(self.min_temperature + steps * self.temperature_step, 3)

    @callback
    def _persist(self) -> None:
        """Persist schedule values in the config entry options."""
        self.hass.config_entries.async_update_entry(
            self.entry,
            options=self.options_snapshot(),
        )

    def options_snapshot(self) -> dict[str, Any]:
        """Return the complete persisted representation of this schedule."""
        return {
            CONF_ENABLED: self.enabled,
            CONF_STANDARD_TEMPERATURE_ENABLED: self.standard_temperature_enabled,
            CONF_STANDARD_TEMPERATURE: self.standard_temperature,
            CONF_PERIOD_COUNT: self.period_count,
            CONF_PERIODS: [dict(period) for period in self.periods],
        }

    @callback
    def _notify_if_changed(self, *, force: bool = False) -> None:
        """Update entities only when their meaningful state changed."""
        snapshot = (
            self.enabled,
            self.standard_temperature_enabled,
            self.standard_temperature,
            self.active_period_index(),
            self.desired_temperature(),
            self.scheduled_temperature(),
            self.status,
            self.last_error,
            self.last_applied,
            self.last_temperature_sent,
            self.last_sync_check,
            tuple(
                (
                    period[PERIOD_ENABLED],
                    period[PERIOD_START],
                    period[PERIOD_TEMPERATURE],
                    period.get(PERIOD_USE_STANDARD_TEMPERATURE, False),
                )
                for period in self.periods
            ),
        )
        if not force and snapshot == self._last_snapshot:
            return
        self._last_snapshot = snapshot
        for listener in tuple(self._listeners):
            listener()
