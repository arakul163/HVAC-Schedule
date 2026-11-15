"""Use the schema implementation provided by the installed Home Assistant version."""

from collections.abc import Callable
from typing import cast

import voluptuous as vol
from homeassistant import data_entry_flow

# Core 2026.11 uses probatio markers for field visibility. Older Core uses voluptuous.
# Keep all markers and schemas from the same implementation within each form.
_schema_module = getattr(data_entry_flow, "probatio", vol)
Schema = cast(type[vol.Schema], _schema_module.Schema)
Required = cast(type[vol.Required], _schema_module.Required)
Optional = cast(type[vol.Optional], _schema_module.Optional)


def optional_when(field: str, *, default: float, controlling_field: str, value: bool) -> vol.Optional:
    """Create a conditional field on supported Core versions, or a normal optional field."""
    native_optional = getattr(data_entry_flow, "Optional", None)
    if native_optional is None:
        return Optional(field, default=default)
    factory = cast(Callable[..., vol.Optional], native_optional)
    return factory(field, default=default, visible={"field": controlling_field, "value": value})
