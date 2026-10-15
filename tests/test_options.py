"""Polling options and coordinator scheduling."""

from unittest.mock import AsyncMock, patch

import probatio
import pytest
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.indevolt_modbus.coordinator import IndevoltCoordinator
from custom_components.indevolt_modbus.vendor.indevolt_modbus import IndevoltDevice

DOMAIN = "indevolt_modbus"
PREFIX = "custom_components.indevolt_modbus"
DATA = {"host": "192.0.2.10", "port": 8899, "unit_id": 1}


@pytest.mark.parametrize("interval", [None, 5, 120, 3600])
async def test_interval_and_options_defaults(hass, unit, interval):
    options = {} if interval is None else {CONF_SCAN_INTERVAL: interval}
    entry = MockConfigEntry(domain=DOMAIN, data=DATA, options=options)
    entry.add_to_hass(hass)
    coordinator = IndevoltCoordinator(hass, entry, IndevoltDevice(unit))
    assert coordinator.regular_interval == (interval or 30)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["data_schema"]({}) == {
        CONF_SCAN_INTERVAL: interval or 30,
        "fast_poll_sensor": "",
        "message_spacing": 2,
    }
    for invalid in (0, -1, 4, 3601, "not a number"):
        with pytest.raises(probatio.Invalid):
            result["data_schema"]({CONF_SCAN_INTERVAL: invalid})


async def test_options_reload_applies_interval_and_releases_unit(hass, unit):
    entry = MockConfigEntry(domain=DOMAIN, data=DATA)
    entry.add_to_hass(hass)
    events = []

    async def acquire(*args):
        events.append("acquire")
        return unit

    async def release(*args):
        events.append("release")

    with (
        patch(f"{PREFIX}.async_get_unit", side_effect=acquire),
        patch(f"{PREFIX}.async_release_unit", side_effect=release),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        old_coordinator = entry.runtime_data
        assert old_coordinator.regular_interval == 30
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {CONF_SCAN_INTERVAL: 120}
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        await hass.async_block_till_done()
        assert entry.options == {
            CONF_SCAN_INTERVAL: 120,
            "fast_poll_sensor": "",
            "message_spacing": 2,
        }
        assert entry.data == DATA
        assert entry.runtime_data is not old_coordinator
        assert entry.runtime_data.regular_interval == 120
        assert not list(old_coordinator.async_contexts())
        assert events == ["acquire", "release", "acquire"]
        assert await hass.config_entries.async_unload(entry.entry_id)
        assert events[-1] == "release"


async def test_options_preserve_other_settings(hass):
    entry = MockConfigEntry(
        domain=DOMAIN, data=DATA, options={"future_setting": True, "message_spacing": 5}
    )
    entry.add_to_hass(hass)
    with patch.object(hass.config_entries, "async_reload", new_callable=AsyncMock):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        await hass.config_entries.options.async_configure(
            result["flow_id"], {CONF_SCAN_INTERVAL: 60}
        )
        await hass.async_block_till_done()
    assert entry.options == {
        "future_setting": True,
        CONF_SCAN_INTERVAL: 60,
        "fast_poll_sensor": "",
        "message_spacing": 5,
    }


async def test_fast_poll_options_validate_and_apply(hass, unit):
    entry = MockConfigEntry(domain=DOMAIN, data=DATA, options={"fast_poll_interval": 2})
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(
        entry.entry_id, context={"show_advanced_options": True}
    )
    schema = result["data_schema"]
    for field, values in {
        "fast_poll_interval": [0, -1, 3601],
        "message_spacing": [0, -1, 61],
    }.items():
        for value in values:
            with pytest.raises(probatio.Invalid):
                schema(
                    {"advanced_polling": {field: value}}
                    if field == "fast_poll_interval"
                    else {field: value}
                )
    options = {
        CONF_SCAN_INTERVAL: 60,
        "fast_poll_interval": 2,
        "message_spacing": 1,
        "fast_poll_sensor": "inv_input_power_174",
    }
    with patch.object(hass.config_entries, "async_reload", new_callable=AsyncMock):
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                key: value
                for key, value in options.items()
                if key != "fast_poll_interval"
            }
            | {"advanced_polling": {"fast_poll_interval": 2}},
        )
        await hass.async_block_till_done()
    assert entry.options == options
    with patch(f"{PREFIX}.async_get_unit", AsyncMock(return_value=unit)):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        coordinator = entry.runtime_data
        assert coordinator.regular_interval == 60
        assert coordinator.fast_interval == 2
        assert coordinator.device.modbus_unit._message_spacing == 1
        assert await hass.config_entries.async_unload(entry.entry_id)


async def test_sensor_selector_scoped_and_stable_across_rename(hass):
    from homeassistant.helpers import entity_registry as er

    entry = MockConfigEntry(domain=DOMAIN, data=DATA)
    entry.add_to_hass(hass)
    other = MockConfigEntry(domain=DOMAIN, data={**DATA, "host": "192.0.2.11"})
    other.add_to_hass(hass)
    registry = er.async_get(hass)
    selected = registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_acout_w_1284",
        config_entry=entry,
        original_name="ACOutW",
    )
    registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_inv_input_power_174",
        config_entry=entry,
        disabled_by=er.RegistryEntryDisabler.USER,
    )
    registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{other.entry_id}_battery_power_6564",
        config_entry=other,
    )
    registry.async_get_or_create(
        "number",
        DOMAIN,
        f"{entry.entry_id}_back_up_soc_1142",
        config_entry=entry,
    )
    registry.async_update_entity(selected.entity_id, new_entity_id="sensor.renamed_ac")
    with patch.object(hass.config_entries, "async_reload", new_callable=AsyncMock):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        schema = result["data_schema"]
        assert "fast_poll_interval" not in {str(k) for k in schema.schema}
        for invalid in (
            "battery_power_6564",
            "inv_input_power_174",
            "back_up_soc_1142",
        ):
            with pytest.raises(probatio.Invalid):
                schema({"fast_poll_sensor": invalid})
        await hass.config_entries.options.async_configure(
            result["flow_id"], {"fast_poll_sensor": "acout_w_1284"}
        )
        await hass.async_block_till_done()
    assert entry.options["fast_poll_sensor"] == "acout_w_1284"
    assert registry.async_get("sensor.renamed_ac") is not None


@pytest.mark.parametrize("interval,target", [(0, ""), (5, "inv_input_power_174")])
async def test_legacy_selection_preserves_interval_on_save(hass, interval, target):
    entry = MockConfigEntry(
        domain=DOMAIN, data=DATA, options={"fast_poll_interval": interval}
    )
    entry.add_to_hass(hass)
    with patch.object(hass.config_entries, "async_reload", new_callable=AsyncMock):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        assert result["data_schema"]({})["fast_poll_sensor"] == target
        await hass.config_entries.options.async_configure(result["flow_id"], {})
        await hass.async_block_till_done()
    assert entry.options["fast_poll_interval"] == interval
    assert entry.options["fast_poll_sensor"] == target
