"""Base entity for HVAC Schedule."""

from __future__ import annotations

from typing import Any

from homeassistant.core import callback
from homeassistant.helpers.entity import Entity

from ..schedule_manager import ScheduleManager


class ScheduleEntity(Entity):
    """Base class for schedule entities."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(
        self,
        manager: ScheduleManager,
        key: str,
        translation_key: str,
        translation_placeholders: dict[str, str] | None = None,
    ) -> None:
        """Initialize a schedule entity."""
        self.manager = manager
        self._attr_unique_id = f"{manager.entry.unique_id}_{key}"
        self._attr_translation_key = translation_key
        if translation_placeholders is not None:
            self._attr_translation_placeholders = translation_placeholders
        self._attr_device_info = manager.device_info
        self._update_from_manager()

    async def async_added_to_hass(self) -> None:
        """Register for manager updates."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.manager.async_add_listener(self._handle_manager_update)
        )

    @callback
    def _handle_manager_update(self) -> None:
        """Refresh attributes and write the latest manager state."""
        self._update_from_manager()
        self.async_write_ha_state()

    def _update_from_manager(self) -> None:
        """Refresh cached Home Assistant entity attributes."""
        self._attr_extra_state_attributes = self._make_extra_state_attributes()

    def _make_extra_state_attributes(self) -> dict[str, Any]:
        """Build entity-specific state attributes."""
        return {"target_entity_id": self.manager.target_entity_id}
