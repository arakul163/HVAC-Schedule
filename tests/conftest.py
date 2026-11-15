"""Shared fixtures for HVAC Schedule tests."""

from collections.abc import Generator

import pytest

pytest_plugins = ["pytest_homeassistant_custom_component"]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> Generator[None, None, None]:
    """Allow the Home Assistant test harness to load custom_components."""
    yield
