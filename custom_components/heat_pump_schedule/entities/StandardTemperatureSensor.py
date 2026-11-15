"""Standard temperature sensor for HVAC Schedule."""

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity

from ..schedule_manager import ScheduleManager
from .schedule_entity import ScheduleEntity


class StandardTemperatureSensor(ScheduleEntity, SensorEntity):
    """Configured standard temperature, independent of the active control mode."""

    _attr_icon = "mdi:thermometer-auto"
    _attr_device_class = SensorDeviceClass.TEMPERATURE

    def __init__(self, manager: ScheduleManager) -> None:
        super().__init__(manager, "standard_temperature", "standard_temperature")
        self._attr_native_unit_of_measurement = manager.temperature_unit

    def _update_from_manager(self) -> None:
        """Refresh the configured standard temperature."""
        super()._update_from_manager()
        self._attr_native_value = self.manager.standard_temperature
