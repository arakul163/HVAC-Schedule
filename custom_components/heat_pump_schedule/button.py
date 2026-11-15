"""Button platform for HVAC Schedule."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entities.apply_schedule_button import ApplyScheduleButton
from .schedule_manager import ScheduleManager


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry[ScheduleManager],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the apply-now button."""
    async_add_entities([ApplyScheduleButton(entry.runtime_data)])
