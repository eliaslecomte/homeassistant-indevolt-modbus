"""Expose version-aware operating modes."""

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import SELECT_ADDRESSES
from .coordinator import IndevoltConfigEntry
from .entity import IndevoltEntity
from .vendor.indevolt_modbus import Register

PARALLEL_UPDATES = 1
# Confirmed equivalents of core HTTP controls; see docs/entity-defaults.md.
DEFAULT_ADDRESSES = {
    1144,  # Energy / system mode.
    7265,  # Front-panel light (also supports half brightness).
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IndevoltConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create supported mode selectors."""
    async_add_entities(
        IndevoltSelect(entry, r)
        for r in entry.runtime_data.device.registers
        if r.address in SELECT_ADDRESSES
    )


class IndevoltSelect(IndevoltEntity, SelectEntity):
    """An enumeration with unsupported firmware options removed."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, entry: IndevoltConfigEntry, register: Register) -> None:
        super().__init__(entry, register)
        self._attr_entity_registry_enabled_default = (
            register.address in DEFAULT_ADDRESSES
        )
        self._attr_options = [str(v) for v in self.coordinator.device.options(register)]

    @property
    def current_option(self) -> str | None:
        """Return a stable translation token for the current code."""
        value = self.coordinator.value(self.register)
        return None if value is None else str(int(value))

    async def async_select_option(self, option: str) -> None:
        """Write and refresh the operating mode."""
        await self._write(int(option))
