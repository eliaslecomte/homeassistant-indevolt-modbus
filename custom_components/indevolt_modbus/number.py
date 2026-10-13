"""Expose settings with documented numeric bounds."""

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import NUMBER_RANGES
from .coordinator import IndevoltConfigEntry
from .entity import IndevoltEntity
from .vendor.indevolt_modbus import Register

PARALLEL_UPDATES = 1
# Confirmed equivalents of core HTTP controls; see docs/entity-defaults.md.
DEFAULT_ADDRESSES = {
    1138,  # Inverter input limit.
    1142,  # Discharge limit / backup SOC.
    1146,  # Feed-in power limit.
    1147,  # Maximum AC output power.
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IndevoltConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create supported numeric settings."""
    async_add_entities(
        IndevoltNumber(entry, r)
        for r in entry.runtime_data.device.registers
        if r.address in NUMBER_RANGES
    )


class IndevoltNumber(IndevoltEntity, NumberEntity):
    """A bounded integer setting."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX
    _attr_native_step = 1

    def __init__(self, entry: IndevoltConfigEntry, register: Register) -> None:
        super().__init__(entry, register)
        self._attr_entity_registry_enabled_default = (
            register.address in DEFAULT_ADDRESSES
        )
        self._attr_native_min_value, self._attr_native_max_value = NUMBER_RANGES[
            register.address
        ]
        self._attr_native_unit_of_measurement = register.unit

    @property
    def native_value(self) -> float | None:
        """Return the last value read from the device."""
        return self.coordinator.value(self.register)

    async def async_set_native_value(self, value: float) -> None:
        """Write and refresh the setting."""
        await self._write(value)
