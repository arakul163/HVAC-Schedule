"""Precise selector module typing for strict type checking."""

from typing import Protocol

from homeassistant.helpers import selector


class TypedSelectorModule(Protocol):
    """Concrete selector types erased by Home Assistant's registry decorator."""

    EntitySelector: type[selector.Selector[selector.EntitySelectorConfig]]
    NumberSelector: type[selector.Selector[selector.NumberSelectorConfig]]
    BooleanSelector: type[selector.Selector[selector.BooleanSelectorConfig]]
    TimeSelector: type[selector.Selector[selector.TimeSelectorConfig]]
