"""Fixed polling and migration from the retired timing options."""

from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.indevolt_modbus import async_migrate_entry
from custom_components.indevolt_modbus.config_flow import IndevoltConfigFlow

DOMAIN = "indevolt_modbus"
PREFIX = "custom_components.indevolt_modbus"
DATA = {"host": "192.0.2.10", "port": 8899, "unit_id": 1}


@pytest.mark.parametrize(
    "legacy",
    [
        {},
        {
            "scan_interval": 120,
            "fast_poll_sensor": "battery_power_6564",
            "fast_poll_interval": 3,
            "message_spacing": 1,
        },
    ],
)
async def test_upgrade_removes_polling_options(hass, unit, legacy):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=DATA,
        options={**legacy, "future_setting": True},
        version=1,
        minor_version=1,
    )
    entry.add_to_hass(hass)
    with patch(f"{PREFIX}.async_get_unit", AsyncMock(return_value=unit)):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.minor_version == 2
        assert entry.options == {"future_setting": True}
        assert entry.data == DATA
        assert not IndevoltConfigFlow.async_supports_options_flow(entry)
        coordinator = entry.runtime_data
        assert coordinator.regular_interval == 60
        assert coordinator.fast_interval == 10
        assert coordinator.fast_sensor == "acout_w_1284"
        assert coordinator.device.modbus_unit._message_spacing == 2
        assert await hass.config_entries.async_unload(entry.entry_id)


async def test_cannot_migrate_future_version(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=DATA, version=2)
    entry.add_to_hass(hass)
    assert not await async_migrate_entry(hass, entry)
    assert entry.version == 2
