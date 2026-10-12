"""Expose typed register readings as sensors."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import NUMBER_RANGES, SELECT_ADDRESSES, SWITCH_ADDRESSES
from .coordinator import IndevoltConfigEntry
from .entity import IndevoltEntity
from .vendor.indevolt_modbus import Register

PARALLEL_UPDATES = 0
UNITS = {
    "W": SensorDeviceClass.POWER,
    "V": SensorDeviceClass.VOLTAGE,
    "A": SensorDeviceClass.CURRENT,
    "Hz": SensorDeviceClass.FREQUENCY,
    "°C": SensorDeviceClass.TEMPERATURE,
}
DEFAULT_ADDRESSES = {2250, 174, 6564, 7599, 7593, 1284, 1269, 1271, 124, 7512}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IndevoltConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create supported sensors, leaving diagnostic registers disabled by default."""
    controls = NUMBER_RANGES.keys() | SELECT_ADDRESSES | SWITCH_ADDRESSES
    async_add_entities(
        IndevoltSensor(entry, r)
        for r in entry.runtime_data.device.registers
        if r.address not in controls
    )


class IndevoltSensor(IndevoltEntity, SensorEntity):
    """A decoded register value."""

    def __init__(self, entry: IndevoltConfigEntry, register: Register) -> None:
        super().__init__(entry, register)
        self._attr_entity_registry_enabled_default = (
            register.address in DEFAULT_ADDRESSES
        )
        if register.group in {"Info", "Event"}:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        if register.options:
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = [
                str(v) for v in self.coordinator.device.options(register)
            ]
        else:
            self._attr_native_unit_of_measurement = register.unit
            self._attr_device_class = UNITS.get(register.unit)
            if register.group == "Real Time Data" and register.unit in UNITS:
                self._attr_state_class = SensorStateClass.MEASUREMENT
            elif register.unit == "Wh" and register.group == "Statistics":
                self._attr_device_class = SensorDeviceClass.ENERGY
                self._attr_state_class = SensorStateClass.TOTAL_INCREASING

    @property
    def native_value(self) -> int | float | str | None:
        """Return the decoded value, including None for unknown codes."""
        value = self.coordinator.device.value(self.register)
        return str(int(value)) if value is not None and self.register.options else value
