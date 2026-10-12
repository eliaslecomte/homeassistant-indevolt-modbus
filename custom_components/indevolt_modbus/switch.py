"""Expose documented enable/disable settings."""

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import SWITCH_ADDRESSES
from .coordinator import IndevoltConfigEntry
from .entity import IndevoltEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IndevoltConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create supported switches."""
    async_add_entities(
        IndevoltSwitch(entry, r)
        for r in entry.runtime_data.device.registers
        if r.address in SWITCH_ADDRESSES
    )


class IndevoltSwitch(IndevoltEntity, SwitchEntity):
    """An explicit zero/one register switch."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False

    @property
    def is_on(self) -> bool | None:
        """Treat unknown codes as unknown, rather than truthy."""
        value = self.coordinator.device.value(self.register)
        return bool(value) if value in (0, 1) else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the setting."""
        await self._write(1)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the setting."""
        await self._write(0)
