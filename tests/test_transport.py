"""Verify fallback and shared API connection ownership."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from modbus_connection import ModbusTcpParams
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.indevolt_modbus import transport


async def test_fallback_closes(hass, unit):
    entry = MockConfigEntry(domain="indevolt_modbus", data={}, title="Indevolt")
    entry.add_to_hass(hass)
    connection = MagicMock()
    connection.for_unit.return_value = unit
    connection.close = AsyncMock()
    with (
        patch.object(transport.modbus, "async_get_unit", None, create=True),
        patch.object(transport, "TmodbusConnection", return_value=connection),
    ):
        assert (
            await transport.async_get_unit(
                hass, entry, ModbusTcpParams(host="192.0.2.1"), 1
            )
            is unit
        )
        await transport.async_release_unit(hass, entry)
        await transport.async_release_unit(hass, entry)
        connection.close.assert_awaited_once()


async def test_probe_closes_on_error(hass, unit):
    connection = MagicMock()
    connection.for_unit.return_value = unit
    connection.close = AsyncMock()
    with (
        patch.object(transport.modbus, "async_get_temporary_unit", None, create=True),
        patch.object(transport, "TmodbusConnection", return_value=connection),
        pytest.raises(ValueError),
    ):
        async with transport.async_get_temporary_unit(
            hass, ModbusTcpParams(host="192.0.2.1"), 1
        ):
            raise ValueError("failed probe")
    connection.close.assert_awaited_once()


async def test_shared_api_ownership(hass, unit):
    entry = MockConfigEntry(domain="indevolt_modbus", data={}, title="Indevolt")
    entry.add_to_hass(hass)
    params = ModbusTcpParams(host="192.0.2.1")

    @asynccontextmanager
    async def temporary(*args):
        yield unit

    with (
        patch.object(
            transport.modbus, "async_get_unit", return_value=unit, create=True
        ) as shared,
        patch.object(
            transport.modbus, "async_get_temporary_unit", temporary, create=True
        ),
        patch.object(transport, "TmodbusConnection") as fallback,
    ):
        assert await transport.async_get_unit(hass, entry, params, 1) is unit
        shared.assert_called_once_with(hass, entry, params, 1)
        async with transport.async_get_temporary_unit(
            hass, params, 1
        ) as temporary_unit:
            assert temporary_unit is unit
        await transport.async_release_unit(hass, entry)
        fallback.assert_not_called()
