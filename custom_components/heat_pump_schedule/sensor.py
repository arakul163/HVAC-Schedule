"""Sensor platform for HVAC Schedule."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entities.StandardTemperatureSensor import StandardTemperatureSensor
from .entities.active_period_sensor import ActivePeriodSensor
from .entities.last_sync_check_sensor import LastSyncCheckSensor
from .entities.last_temperature_sent_sensor import LastTemperatureSentSensor
from .entities.period_summary_sensor import PeriodSummarySensor
from .entities.schedule_status_sensor import ScheduleStatusSensor
from .entities.scheduled_temperature_sensor import ScheduledTemperatureSensor
from .schedule_manager import ScheduleManager


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry[ScheduleManager],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up status sensors."""
    manager = entry.runtime_data
    async_add_entities(
        [
            ScheduledTemperatureSensor(manager),
            ActivePeriodSensor(manager),
            ScheduleStatusSensor(manager),
            LastTemperatureSentSensor(manager),
            LastSyncCheckSensor(manager),
            *(PeriodSummarySensor(manager, index) for index in range(manager.period_count)),
            StandardTemperatureSensor(manager),
        ]
    )
