"""Period summary sensor for HVAC Schedule."""

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity

from ..schedule_manager import ScheduleManager
from .schedule_entity import ScheduleEntity


class PeriodSummarySensor(ScheduleEntity, SensorEntity):
    """Read-only summary of one configured schedule period."""

    _attr_device_class = SensorDeviceClass.ENUM

    def __init__(self, manager: ScheduleManager, index: int) -> None:
        self._attr_options = ["active", "disabled"]
        self.index = index
        number = index + 1
        super().__init__(
            manager,
            f"period_{number}_summary",
            "period_summary",
            {
                "period": str(number),
                "start": manager.period_start(index).strftime("%H:%M"),
                "temperature": self._format_temperature(manager.period_temperature(index)),
                "unit": manager.temperature_unit,
            },
        )

    def _update_from_manager(self) -> None:
        """Refresh the current period state."""
        super()._update_from_manager()
        self._attr_native_value = "active" if self.manager.period_enabled(self.index) else "disabled"
        self._attr_icon = (
            "mdi:clock-check-outline" if self.manager.period_enabled(self.index) else "mdi:clock-remove-outline"
        )

    def _make_extra_state_attributes(self) -> dict[str, Any]:
        """Build the current period attributes."""
        return {
            "target_entity_id": self.manager.target_entity_id,
            "period": self.index + 1,
            "start": self.manager.period_start(self.index).isoformat(),
            "temperature": self.manager.period_temperature(self.index),
            "enabled": self.manager.period_enabled(self.index),
            "use_standard_temperature": self.manager.period_uses_standard_temperature(self.index),
        }

    @staticmethod
    def _format_temperature(value: float) -> str:
        """Format a temperature without unnecessary trailing zeroes."""
        return f"{value:.3f}".rstrip("0").rstrip(".")
