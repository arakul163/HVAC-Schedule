"""Home Assistant config flow entry point."""

from .subflows.schedule_config_flow import ScheduleConfigFlow

__all__ = ["ScheduleConfigFlow"]
