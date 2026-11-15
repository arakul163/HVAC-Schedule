"""Compatibility checks for conditional configuration fields."""

from unittest.mock import patch

from homeassistant import data_entry_flow

from custom_components.heat_pump_schedule.subflows import flow_schema


def test_conditional_field_uses_native_visibility_api() -> None:
    """Forward the condition to Core's marker and retain that marker in the form schema."""
    native_marker = flow_schema.Optional("temperature", default=31.0)
    with patch.object(data_entry_flow, "Optional", create=True, return_value=native_marker) as factory:
        marker = flow_schema.optional_when(
            "temperature", default=31.0, controlling_field="use_standard_temperature", value=False,
        )
    factory.assert_called_once_with(
        "temperature", default=31.0, visible={"field": "use_standard_temperature", "value": False},
    )
    schema = flow_schema.Schema({marker: float})
    assert next(iter(schema.schema)) is native_marker


def test_conditional_field_keeps_older_core_compatible() -> None:
    """A Core without visibility support still receives a valid optional field."""
    with patch.object(data_entry_flow, "Optional", None, create=True):
        marker = flow_schema.optional_when(
            "temperature", default=31.0, controlling_field="use_standard_temperature", value=False,
        )
    schema = flow_schema.Schema({marker: float})
    assert schema({}) == {"temperature": 31.0}
    assert schema({"temperature": 28.0}) == {"temperature": 28.0}
