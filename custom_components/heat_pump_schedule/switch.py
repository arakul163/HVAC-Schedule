"""Switch platform for HVAC Schedule."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entities.StandardTemperatureSwitch import StandardTemperatureSwitch
from .entities.schedule_enabled_switch import ScheduleEnabledSwitch
from .schedule_manager import ScheduleManager


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry[ScheduleManager],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up switches for one installed schedule."""
    async_add_entities([ScheduleEnabledSwitch(entry.runtime_data), StandardTemperatureSwitch(entry.runtime_data)])
