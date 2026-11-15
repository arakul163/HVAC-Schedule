"""Base timestamp sensor for HVAC Schedule."""

from datetime import datetime
from typing import cast

from homeassistant.components.sensor import RestoreSensor, SensorDeviceClass
from homeassistant.const import EntityCategory

from .schedule_entity import ScheduleEntity


class RestoredTimestampSensor(ScheduleEntity, RestoreSensor):
    """Base class for a diagnostic timestamp restored across restarts."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    manager_attribute: str

    def _update_from_manager(self) -> None:
        """Refresh the timestamp from the manager."""
        super()._update_from_manager()
        self._attr_native_value = cast(datetime | None, getattr(self.manager, self.manager_attribute))

    async def async_added_to_hass(self) -> None:
        """Restore the previous timestamp before writing the initial state."""
        await super().async_added_to_hass()
        if self.native_value is not None:
            return
        restored = await self.async_get_last_sensor_data()
        if restored is not None and isinstance(restored.native_value, datetime):
            setattr(self.manager, self.manager_attribute, restored.native_value)
            self._update_from_manager()
