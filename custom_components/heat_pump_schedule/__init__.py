"""HVAC Schedule integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import entity_registry as er

from .const import CONF_TARGET_ENTITY, MAX_PERIOD_COUNT, PLATFORMS
from .schedule_manager import ScheduleManager


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry[ScheduleManager]
) -> bool:
    """Set up a schedule from a config entry."""
    target_entity = entry.data[CONF_TARGET_ENTITY]
    if hass.states.get(target_entity) is None:
        raise ConfigEntryNotReady(
            f"Climate entity {target_entity} is not available yet"
        )

    manager = ScheduleManager(hass, entry)
    entry.runtime_data = manager
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    _cleanup_period_entities(hass, entry, manager.period_count)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await manager.async_setup()
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: ConfigEntry[ScheduleManager]
) -> bool:
    """Unload a schedule config entry."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False

    await entry.runtime_data.async_unload()
    return True


async def _async_options_updated(
    hass: HomeAssistant, entry: ConfigEntry[ScheduleManager]
) -> None:
    """Reload when the options wizard changed the running schedule."""
    manager: ScheduleManager = entry.runtime_data
    if dict(entry.options) != manager.options_snapshot():
        await hass.config_entries.async_reload(entry.entry_id)


def _cleanup_period_entities(
    hass: HomeAssistant,
    entry: ConfigEntry[ScheduleManager],
    period_count: int,
) -> None:
    """Remove editable controls and summaries beyond the configured count."""
    obsolete_unique_ids = {
        f"{entry.unique_id}_period_{number}_{field}"
        for number in range(1, MAX_PERIOD_COUNT + 1)
        for field in ("enabled", "start", "temperature")
    }
    obsolete_unique_ids.update(
        f"{entry.unique_id}_period_{number}_summary"
        for number in range(period_count + 1, MAX_PERIOD_COUNT + 1)
    )
    registry = er.async_get(hass)
    for registry_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        if registry_entry.unique_id in obsolete_unique_ids:
            registry.async_remove(registry_entry.entity_id)
