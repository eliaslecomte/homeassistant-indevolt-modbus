"""Poll only subsystems required by enabled entities."""

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from modbus_connection import ModbusError
from modbus_connection.model import UpdateReport

from .const import DOMAIN, SCAN_INTERVAL
from .vendor.indevolt_modbus import IndevoltDevice

_LOGGER = logging.getLogger(__name__)
type IndevoltConfigEntry = ConfigEntry[IndevoltCoordinator]


class IndevoltCoordinator(DataUpdateCoordinator[UpdateReport]):
    """Refresh enabled functional subsystems and retain partial availability."""

    def __init__(
        self, hass: HomeAssistant, entry: IndevoltConfigEntry, device: IndevoltDevice
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL),
        )
        self.device = device

    async def _async_update_data(self) -> UpdateReport:
        try:
            await self.device.async_ensure_setup()
            names = set(self.async_contexts()) or {"system_info"}
            report = await self.device.async_update(sorted(names))
        except (ModbusError, ValueError) as err:
            raise UpdateFailed(str(err)) from err
        if not report.updated:
            raise UpdateFailed("No requested subsystem answered")
        return report
