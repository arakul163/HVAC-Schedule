"""Constants for the HVAC Schedule integration."""

from homeassistant.const import Platform

DOMAIN = "heat_pump_schedule"

CONF_TARGET_ENTITY = "target_entity"
CONF_PERIOD_COUNT = "period_count"
CONF_ENABLED = "enabled"
CONF_STANDARD_TEMPERATURE = "standard_temperature"
CONF_STANDARD_TEMPERATURE_ENABLED = "standard_temperature_enabled"
CONF_PERIODS = "periods"

PERIOD_ENABLED = "enabled"
PERIOD_START = "start"
PERIOD_TEMPERATURE = "temperature"
PERIOD_USE_STANDARD_TEMPERATURE = "use_standard_temperature"

DEFAULT_PERIOD_COUNT = 6
MIN_PERIOD_COUNT = 1
MAX_PERIOD_COUNT = 12

PLATFORMS: list[Platform] = [
    Platform.SWITCH,
    Platform.SENSOR,
    Platform.BUTTON,
]
