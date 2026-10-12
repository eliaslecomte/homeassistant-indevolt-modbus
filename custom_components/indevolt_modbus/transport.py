"""Use core's shared connection API, with an entry-owned fallback on older core."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from homeassistant.components import modbus
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import Event, HomeAssistant
from modbus_connection import ModbusTcpParams, ModbusUnit
from modbus_connection.tmodbus import TmodbusConnection

# Fallback connections are private to this custom integration, not a replacement
# for core's shared pool. Do not configure another poller for the same endpoint.
_CONNECTIONS = "indevolt_fallback_connections"


async def async_get_unit(
    hass: HomeAssistant, entry: ConfigEntry, params: ModbusTcpParams, unit_id: int
) -> ModbusUnit:
    """Acquire an entry's unit without opening the socket until the first read."""
    if shared := getattr(modbus, "async_get_unit", None):
        return shared(hass, entry, params, unit_id)
    connection = TmodbusConnection(params)
    hass.data.setdefault(_CONNECTIONS, {})[entry.entry_id] = connection

    async def close_on_stop(event: Event) -> None:
        await async_release_unit(hass, entry)

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, close_on_stop)
    )
    return connection.for_unit(unit_id)


async def async_release_unit(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Close a fallback socket on failed setup, unload, or shutdown."""
    if connection := hass.data.get(_CONNECTIONS, {}).pop(entry.entry_id, None):
        await connection.close()


@asynccontextmanager
async def async_get_temporary_unit(
    hass: HomeAssistant, params: ModbusTcpParams, unit_id: int
) -> AsyncIterator[ModbusUnit]:
    """Release a configuration probe even when cancelled or unsuccessful."""
    if shared := getattr(modbus, "async_get_temporary_unit", None):
        async with shared(hass, params, unit_id) as unit:
            yield unit
        return
    connection = TmodbusConnection(params)
    try:
        yield connection.for_unit(unit_id)
    finally:
        await connection.close()
