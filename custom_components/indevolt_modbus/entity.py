"""Shared identity, availability and write behavior."""

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from modbus_connection import ModbusError

from .const import DOMAIN
from .coordinator import IndevoltConfigEntry, IndevoltCoordinator
from .vendor.indevolt_modbus import Register


class IndevoltEntity(CoordinatorEntity[IndevoltCoordinator]):
    """Represent a register on one independently polled subsystem."""

    _attr_has_entity_name = True

    def __init__(self, entry: IndevoltConfigEntry, register: Register) -> None:
        super().__init__(entry.runtime_data, context=register.component)
        self.register = register
        self._attr_unique_id = f"{entry.entry_id}_{register.key}"
        self._attr_translation_key = register.key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer="Indevolt",
            name=entry.title,
        )

    @property
    def available(self) -> bool:
        """Only consider data from a successful poll of this subsystem."""
        return (
            super().available
            and self.register.component in self.coordinator.data.updated
        )

    async def _write(self, value: float) -> None:
        try:
            await self.coordinator.device.async_write(self.register, value)
        except (ModbusError, ValueError, AttributeError) as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="write_failed"
            ) from err
        await self.coordinator.async_request_refresh()
