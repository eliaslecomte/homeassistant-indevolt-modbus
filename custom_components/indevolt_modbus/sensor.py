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
from .formatting import format_register_value
from .vendor.indevolt_modbus import Register

PARALLEL_UPDATES = 0
UNITS = {
    "W": SensorDeviceClass.POWER,
    "VA": SensorDeviceClass.APPARENT_POWER,
    "var": SensorDeviceClass.REACTIVE_POWER,
    "h": SensorDeviceClass.DURATION,
    "min": SensorDeviceClass.DURATION,
    "V": SensorDeviceClass.VOLTAGE,
    "A": SensorDeviceClass.CURRENT,
    "Hz": SensorDeviceClass.FREQUENCY,
    "°C": SensorDeviceClass.TEMPERATURE,
}
# Semantic matches to the built-in HTTP integration's enabled sensors.
# See indevolt-hacs/docs/sensor-defaults.md for sources and ambiguous matches.
# Registry defaults apply only when HA creates an entity; never migrate choices.
DEFAULT_ADDRESSES = {
    1284,  # Total AC power, suggested fast feedback for energy accounting.
    89,  # System rated battery capacity (Wh).
    124,  # Daily PV generation (Wh).
    1269,  # Total battery charging energy (Wh).
    1271,  # Total battery discharging energy (Wh).
    2250,  # Total PV power (W).
    6563,  # Overall battery charging/discharging state.
    6564,  # Total battery power (W).
    7512,  # Total PV generation (Wh).
    7519,  # Daily battery charging energy (Wh).
    7521,  # Daily battery discharging energy (Wh).
    7553,  # Bypass power (W).
    7599,  # Full-system SOC (%), available from protocol V1.8.
}

# Confirmed core diagnostic families retain their existing sensor identities,
# including HTTP binary sensors represented here as enum/numeric sensors.
DIAGNOSTIC_ADDRESSES = {
    1246,  # Meter connectivity.
    6008,
    6120,
    6232,
    6344,
    6456,
    6731,  # Per-pack cycle counts.
    6010,
    6122,
    6234,
    6346,
    6458,
    6733,  # Per-pack voltage.
    6108,
    6220,
    6332,
    6444,
    6556,
    6831,  # Per-pack current.
    6593,
    6625,
    6657,
    6689,
    6721,
    6865,  # Per-pack heater state.
    7241,  # Standalone/master/slave cluster role (not energy mode).
    7593,
    7594,
    7595,
    7596,
    7597,
    7598,  # Per-pack SOC, not system SOC.
}


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
        if register.address != 89 and (
            register.group in {"Info", "Event"}
            or register.address in DIAGNOSTIC_ADDRESSES
            or register.unit == "°C"
        ):
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
        value = self.coordinator.value(self.register)
        if value is None:
            return None
        if self.register.display_format:
            return format_register_value(int(value), self.register.display_format)
        return str(int(value)) if self.register.options else value

    @property
    def extra_state_attributes(self) -> dict[str, int | float | None] | None:
        """Retain the raw value for diagnosis of formatted versions and times."""
        if self.register.display_format:
            return {"raw_value": self.coordinator.value(self.register)}
        return None
