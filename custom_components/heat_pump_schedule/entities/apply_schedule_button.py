"""Apply-now button for HVAC Schedule."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from ..schedule_manager import ScheduleManager
from .schedule_entity import ScheduleEntity


class ApplyScheduleButton(ScheduleEntity, ButtonEntity):
    """Force the active period temperature to the climate entity."""

    _attr_icon = "mdi:play-circle-outline"

    def __init__(self, manager: ScheduleManager) -> None:
        super().__init__(manager, "apply_now", "apply_now")

    async def async_press(self) -> None:
        await self.manager.async_apply(force=True)
