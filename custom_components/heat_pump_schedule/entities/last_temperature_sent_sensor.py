"""Last temperature command sensor for HVAC Schedule."""

from ..schedule_manager import ScheduleManager
from .restored_timestamp_sensor import RestoredTimestampSensor


class LastTemperatureSentSensor(RestoredTimestampSensor):
    """Last time a target-temperature command was sent to the climate entity."""

    _attr_icon = "mdi:swap-horizontal-bold"
    manager_attribute = "last_temperature_sent"

    def __init__(self, manager: ScheduleManager) -> None:
        super().__init__(manager, "last_temperature_sent", "last_temperature_sent")
