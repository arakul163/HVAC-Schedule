"""Switch entities for HVAC Schedule."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from ..schedule_manager import ScheduleManager
from .schedule_entity import ScheduleEntity


class StandardTemperatureSwitch(ScheduleEntity, SwitchEntity):
    """Enable constant temperature control while the schedule is disabled."""

    _attr_icon = "mdi:thermometer"

    def __init__(self, manager: ScheduleManager) -> None:
        super().__init__(manager, "standard_temperature_enabled", "standard_temperature_enabled")

    def _update_from_manager(self) -> None:
        """Refresh the enabled state."""
        super()._update_from_manager()
        self._attr_is_on = self.manager.standard_temperature_enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.manager.async_set_standard_temperature_enabled(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.manager.async_set_standard_temperature_enabled(False)
