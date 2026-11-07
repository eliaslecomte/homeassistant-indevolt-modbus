"""Integrate Indevolt storage devices using the shared Modbus connection."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from modbus_connection import ModbusTcpParams

from .const import CONF_UNIT_ID, DOMAIN, MESSAGE_SPACING
from .coordinator import IndevoltConfigEntry, IndevoltCoordinator
from .transport import async_get_unit, async_release_unit
from .vendor.indevolt_modbus import IndevoltDevice

PLATFORMS = [Platform.SENSOR, Platform.NUMBER, Platform.SELECT, Platform.SWITCH]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup_entry(hass: HomeAssistant, entry: IndevoltConfigEntry) -> bool:
    """Set up an entry; the Modbus integration owns connection lifetime."""
    unit = await async_get_unit(
        hass,
        entry,
        ModbusTcpParams(host=entry.data[CONF_HOST], port=entry.data[CONF_PORT]),
        entry.data[CONF_UNIT_ID],
    )
    coordinator = IndevoltCoordinator(
        hass,
        entry,
        IndevoltDevice(
            unit,
            message_spacing=MESSAGE_SPACING,
        ),
    )
    try:
        await coordinator.async_config_entry_first_refresh()
        entry.runtime_data = coordinator
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        coordinator.async_start()
    except BaseException:
        await coordinator.async_shutdown()
        await async_release_unit(hass, entry)
        raise
    return True


async def async_unload_entry(hass: HomeAssistant, entry: IndevoltConfigEntry) -> bool:
    """Unload an entry and its platform listeners."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    await entry.runtime_data.async_shutdown()
    await async_release_unit(hass, entry)
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Discard obsolete polling options when upgrading existing entries."""
    if entry.version > 1:
        return False
    if entry.minor_version < 2:
        obsolete = {
            "scan_interval",
            "fast_poll_sensor",
            "fast_poll_interval",
            "message_spacing",
        }
        hass.config_entries.async_update_entry(
            entry,
            options={
                key: value
                for key, value in entry.options.items()
                if key not in obsolete
            },
            minor_version=2,
        )
    return True
