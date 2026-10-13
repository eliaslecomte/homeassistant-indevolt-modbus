"""Configuration, polling, control and lifecycle tests."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import HomeAssistantError
from modbus_connection import ModbusConnectionError
from pytest_homeassistant_custom_component.common import MockConfigEntry

DOMAIN = "indevolt_modbus"
DATA = {"host": "192.0.2.10", "port": 8899, "unit_id": 1}
PREFIX = "custom_components.indevolt_modbus"


async def test_flow_and_duplicate(hass, unit):
    @asynccontextmanager
    async def temporary(*args):
        yield unit

    with (
        patch(f"{PREFIX}.config_flow.async_get_temporary_unit", temporary),
        patch(f"{PREFIX}.async_setup_entry", return_value=True),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        assert result["type"] is FlowResultType.FORM
        result = await hass.config_entries.flow.async_configure(result["flow_id"], DATA)
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"] == DATA
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}, data=DATA
        )
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "already_configured"


@pytest.mark.parametrize("invalid", [False, True])
async def test_probe_errors(hass, unit, invalid):
    @asynccontextmanager
    async def temporary(*args):
        if invalid:
            unit.holding[7534] = 0
        else:
            raise ModbusConnectionError("offline")
        yield unit

    with patch(f"{PREFIX}.config_flow.async_get_temporary_unit", temporary):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}, data=DATA
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"]["base"] == (
            "invalid_device" if invalid else "cannot_connect"
        )


async def test_setup_entities_writes_and_unload(hass, unit):
    entry = MockConfigEntry(domain=DOMAIN, data=DATA, title="Indevolt")
    entry.add_to_hass(hass)
    with (
        patch(f"{PREFIX}.async_get_unit", AsyncMock(return_value=unit)),
        patch(f"{PREFIX}.async_release_unit", new_callable=AsyncMock) as release,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state is ConfigEntryState.LOADED
        await entry.runtime_data.async_refresh()
        states = hass.states.async_all("sensor")
        assert any(state.state == "1234" for state in states)
        assert any(state.state == "76.5" for state in states)
        # Exercise the actual control classes, including validation and readback.
        from custom_components.indevolt_modbus.number import IndevoltNumber
        from custom_components.indevolt_modbus.select import IndevoltSelect
        from custom_components.indevolt_modbus.switch import IndevoltSwitch

        registers = {r.address: r for r in entry.runtime_data.device.registers}
        number = IndevoltNumber(entry, registers[1142])
        select = IndevoltSelect(entry, registers[1144])
        switch = IndevoltSwitch(entry, registers[1143])
        with patch.object(
            entry.runtime_data, "async_request_refresh", new_callable=AsyncMock
        ):
            await number.async_set_native_value(30)
            await select.async_select_option("4")
            await switch.async_turn_on()
            assert unit.holding[1142] == 30
            assert unit.holding[1144] == 4
            assert unit.holding[1143] == 1
            with pytest.raises(HomeAssistantError):
                await number.async_set_native_value(101)
        assert await hass.config_entries.async_unload(entry.entry_id)
        release.assert_awaited_once()


async def test_setup_failure_releases_connection(hass, unit):
    entry = MockConfigEntry(domain=DOMAIN, data=DATA, title="Indevolt")
    entry.add_to_hass(hass)
    unit.fail_read(70, ModbusConnectionError("offline"))
    with (
        patch(f"{PREFIX}.async_get_unit", AsyncMock(return_value=unit)),
        patch(f"{PREFIX}.async_release_unit", new_callable=AsyncMock) as release,
    ):
        assert not await hass.config_entries.async_setup(entry.entry_id)
        assert entry.state is ConfigEntryState.SETUP_RETRY
        release.assert_awaited_once()


async def test_reconfigure(hass, unit):
    entry = MockConfigEntry(domain=DOMAIN, data=DATA, title="Indevolt")
    entry.add_to_hass(hass)

    @asynccontextmanager
    async def temporary(*args):
        yield unit

    with (
        patch(f"{PREFIX}.config_flow.async_get_temporary_unit", temporary),
        patch(f"{PREFIX}.async_setup_entry", return_value=True),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "reconfigure", "entry_id": entry.entry_id}
        )
        assert result["type"] is FlowResultType.FORM
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {**DATA, "host": "192.0.2.11"}
        )
        assert result["reason"] == "reconfigure_successful"
        assert entry.data["host"] == "192.0.2.11"


async def test_partial_availability_and_diagnostics(hass, unit):
    from modbus_connection import IllegalDataAddressError

    from custom_components.indevolt_modbus.diagnostics import (
        async_get_config_entry_diagnostics,
    )
    from custom_components.indevolt_modbus.sensor import IndevoltSensor

    entry = MockConfigEntry(domain=DOMAIN, data=DATA, title="Indevolt")
    entry.add_to_hass(hass)
    with patch(f"{PREFIX}.async_get_unit", AsyncMock(return_value=unit)):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        coordinator = entry.runtime_data
        registers = {r.address: r for r in coordinator.device.registers}
        pv = IndevoltSensor(entry, registers[2250])
        battery = IndevoltSensor(entry, registers[7599])
        await coordinator.async_refresh()
        assert pv.available and battery.available
        unit.fail_read(2250, IllegalDataAddressError())
        await coordinator.async_refresh()
        assert not pv.available
        assert battery.available
        diagnostics = await async_get_config_entry_diagnostics(hass, entry)
        assert diagnostics["protocol_version"] == 19
        assert diagnostics["failed"] == {
            "pv_total_power_2250": "IllegalDataAddressError"
        }
        assert DATA["host"] not in str(diagnostics)
        unit.fail_read(2250, None)
        await coordinator.async_refresh()
        assert pv.available
        await hass.config_entries.async_unload(entry.entry_id)


async def test_platform_failure_releases_connection(hass, unit):
    entry = MockConfigEntry(domain=DOMAIN, data=DATA, title="Indevolt")
    entry.add_to_hass(hass)
    with (
        patch(f"{PREFIX}.async_get_unit", AsyncMock(return_value=unit)),
        patch(f"{PREFIX}.async_release_unit", new_callable=AsyncMock) as release,
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            side_effect=RuntimeError("failure"),
        ),
    ):
        assert not await hass.config_entries.async_setup(entry.entry_id)
    release.assert_awaited_once()


@pytest.mark.parametrize("duplicate", [False, True])
async def test_reconfigure_errors(hass, unit, duplicate):
    entry = MockConfigEntry(domain=DOMAIN, data=DATA, title="Indevolt")
    entry.add_to_hass(hass)
    new_data = {**DATA, "host": "192.0.2.11"}
    if duplicate:
        MockConfigEntry(domain=DOMAIN, data=new_data, title="Other").add_to_hass(hass)

    @asynccontextmanager
    async def temporary(*args):
        raise ModbusConnectionError("offline")
        yield unit

    with patch(f"{PREFIX}.config_flow.async_get_temporary_unit", temporary):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "reconfigure", "entry_id": entry.entry_id},
            data=new_data,
        )
        if duplicate:
            assert result["type"] is FlowResultType.ABORT
            assert result["reason"] == "already_configured"
        else:
            assert result["type"] is FlowResultType.FORM
            assert result["errors"] == {"base": "cannot_connect"}
        assert entry.data == DATA


async def test_diagnostics_before_setup(hass):
    from custom_components.indevolt_modbus.diagnostics import (
        async_get_config_entry_diagnostics,
    )

    entry = MockConfigEntry(domain=DOMAIN, data=DATA, title="Indevolt")
    entry.add_to_hass(hass)
    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    assert diagnostics == {"setup_complete": False, "state": "not_loaded"}
    assert DATA["host"] not in str(diagnostics)
