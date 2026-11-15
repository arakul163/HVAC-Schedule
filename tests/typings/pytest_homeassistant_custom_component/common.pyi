from collections.abc import Mapping
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

class MockConfigEntry(ConfigEntry[Any]):
    def __init__(
        self,
        *,
        data: Mapping[str, Any] | None = ...,
        domain: str = ...,
        entry_id: str | None = ...,
        options: Mapping[str, Any] | None = ...,
        title: str = ...,
        unique_id: str | None = ...,
        **kwargs: Any,
    ) -> None: ...
    def add_to_hass(self, hass: HomeAssistant) -> None: ...
