"""Active period sensor for HVAC Schedule."""

from typing import Any

from homeassistant.components.sensor import SensorEntity

from ..schedule_manager import ScheduleManager
from .schedule_entity import ScheduleEntity


class ActivePeriodSensor(ScheduleEntity, SensorEntity):
    """Number of the currently active period."""

    _attr_icon = "mdi:clock-check-outline"

    def __init__(self, manager: ScheduleManager) -> None:
        super().__init__(manager, "active_period", "active_period")

    def _update_from_manager(self) -> None:
        """Refresh the active period."""
        super()._update_from_manager()
        index = self.manager.active_period_index()
        self._attr_native_value = None if index is None else index + 1

    def _make_extra_state_attributes(self) -> dict[str, Any]:
        """Build the active period attributes."""
        attributes: dict[str, Any] = {"target_entity_id": self.manager.target_entity_id}
        index = self.manager.active_period_index()
        if index is not None:
            attributes["start"] = self.manager.period_start(index).isoformat()
            attributes["temperature"] = self.manager.period_temperature(index)
        return attributes
