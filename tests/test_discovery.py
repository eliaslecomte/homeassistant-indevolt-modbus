"""Discovery supplies candidates, never inferred Modbus identity or ports."""

from ipaddress import ip_address
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
from pytest_homeassistant_custom_component.common import MockConfigEntry

DOMAIN = "indevolt_modbus"
DATA = {"host": "192.0.2.10", "port": 8899, "unit_id": 1}
PREFIX = "custom_components.indevolt_modbus"


def discovery(host="192.0.2.10"):
    address = ip_address(host)
    return ZeroconfServiceInfo(
        ip_address=address,
        ip_addresses=[address],
        port=8080,
        hostname="unverified-serial.local.",
        type="_http._tcp.local.",
        name="igen_fw test._http._tcp.local.",
        properties={},
    )


async def start(hass, host="192.0.2.10"):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "zeroconf"}, data=discovery(host)
    )


async def test_discovery_confirm(hass):
    with (
        patch(
            f"{PREFIX}.config_flow.IndevoltConfigFlow._validate", return_value=None
        ) as validate,
        patch(f"{PREFIX}.async_setup_entry", return_value=True),
    ):
        result = await start(hass)
        assert result["step_id"] == "discovery_confirm"
        validate.assert_not_called()
        suggested = {
            str(key): key.description["suggested_value"]
            for key in result["data_schema"].schema
        }
        assert suggested == DATA
        # An installation may use nondefault Modbus settings.
        data = {**DATA, "port": 9000, "unit_id": 2}
        result = await hass.config_entries.flow.async_configure(result["flow_id"], data)
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"] == data
        assert result["options"] == {
            "fast_poll_sensor": "acout_w_1284",
            "fast_poll_interval": 3,
        }
        assert result["result"].unique_id is None
        validate.assert_awaited_once_with(data)


@pytest.mark.parametrize("error", ["cannot_connect", "invalid_device"])
async def test_discovery_validation_errors(hass, error):
    with patch(
        f"{PREFIX}.config_flow.IndevoltConfigFlow._validate", return_value=error
    ):
        result = await start(hass)
        result = await hass.config_entries.flow.async_configure(result["flow_id"], DATA)
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "discovery_confirm"
        assert result["errors"] == {"base": error}


async def test_existing_entry_suppresses_discovery(hass):
    MockConfigEntry(domain=DOMAIN, data=DATA).add_to_hass(hass)
    with patch(f"{PREFIX}.config_flow.async_get_temporary_unit") as probe:
        result = await start(hass, "192.0.2.11")
        assert result["reason"] == "already_configured"
        probe.assert_not_called()


async def test_concurrent_discovery(hass):
    first = await start(hass)
    second = await start(hass, "192.0.2.11")
    assert first["type"] is FlowResultType.FORM
    assert second["reason"] == "already_in_progress"


async def test_duplicate_created_while_confirming(hass):
    result = await start(hass)
    MockConfigEntry(domain=DOMAIN, data=DATA).add_to_hass(hass)
    with patch(
        f"{PREFIX}.config_flow.IndevoltConfigFlow._validate", new_callable=AsyncMock
    ) as validate:
        result = await hass.config_entries.flow.async_configure(result["flow_id"], DATA)
        assert result["reason"] == "already_configured"
        validate.assert_not_called()


async def test_ignored_discovery(hass):
    from homeassistant.config_entries import DEFAULT_DISCOVERY_UNIQUE_ID

    MockConfigEntry(
        domain=DOMAIN, source="ignore", unique_id=DEFAULT_DISCOVERY_UNIQUE_ID, data={}
    ).add_to_hass(hass)
    result = await start(hass)
    assert result["reason"] == "already_configured"
