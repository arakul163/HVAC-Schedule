"""Schedule status sensor for HVAC Schedule."""

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity

from ..schedule_manager import ScheduleManager
from .schedule_entity import ScheduleEntity


class ScheduleStatusSensor(ScheduleEntity, SensorEntity):
    """Diagnostic state of the installed schedule."""

    _attr_icon = "mdi:calendar-check"
    _attr_device_class = SensorDeviceClass.ENUM

    def __init__(self, manager: ScheduleManager) -> None:
        self._attr_options = ["standard_temperature", "disabled", "no_enabled_periods", "target_unavailable", "error", "active"]
        super().__init__(manager, "status", "schedule_status")

    def _update_from_manager(self) -> None:
        """Refresh the schedule status."""
        super()._update_from_manager()
        self._attr_native_value = self.manager.status

    def _make_extra_state_attributes(self) -> dict[str, Any]:
        """Build the current status attributes."""
        return {
            "target_entity_id": self.manager.target_entity_id,
            "last_error": self.manager.last_error,
            "last_applied": self.manager.last_applied.isoformat() if self.manager.last_applied is not None else None,
            "last_applied_temperature": self.manager.last_applied_temperature,
        }
