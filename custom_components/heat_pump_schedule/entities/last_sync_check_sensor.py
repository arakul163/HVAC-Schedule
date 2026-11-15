"""Last synchronization sensor for HVAC Schedule."""

from ..schedule_manager import ScheduleManager
from .restored_timestamp_sensor import RestoredTimestampSensor


class LastSyncCheckSensor(RestoredTimestampSensor):
    """Last time the scheduled and target temperatures were compared."""

    _attr_icon = "mdi:sync"
    manager_attribute = "last_sync_check"

    def __init__(self, manager: ScheduleManager) -> None:
        super().__init__(manager, "last_sync_check", "last_sync_check")
