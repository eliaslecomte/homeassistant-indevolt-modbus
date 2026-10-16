"""Documented packed values must be readable without changing protocol data."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.indevolt_modbus.formatting import format_register_value
from custom_components.indevolt_modbus.vendor.indevolt_modbus import REGISTERS


@pytest.mark.parametrize(
    ("kind", "raw", "expected"),
    [
        ("firmware", 10112, "V1.01.12"),
        ("firmware", 14501, "V1.45.01"),
        ("firmware", 0, "V0.00.00"),
        ("inverter_version", 141, "V1.41"),
        ("protocol_version", 24, "V2.4"),
        ("hour_minute", 0x121E, "18:30"),
        ("hour_minute", 0, "00:00"),
        ("hour_minute", 0x173B, "23:59"),
        ("hour_minute", 0x1800, None),
        ("hour_minute", 0x003C, None),
        ("hour_minute", 65535, None),
        ("year_month", 0x1A0A, "2026-10"),
        ("year_month", 0, None),
        ("year_month", 0x6401, None),
        ("day_hour", 0x1010, "Day 16, hour 16"),
        ("day_hour", 0, None),
        ("day_hour", 0x2010, None),
        ("minute_second", 0x3B3B, "59:59"),
        ("minute_second", 0x3C00, None),
        ("firmware", -1, None),
        ("firmware", 65536, None),
    ],
)
def test_documented_format(kind, raw, expected):
    assert format_register_value(raw, kind) == expected


async def test_formatted_sensor_keeps_identity_and_raw_value(hass, unit):
    entry = MockConfigEntry(
        domain="indevolt_modbus",
        data={"host": "192.0.2.10", "port": 8899, "unit_id": 1},
    )
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    keys = ["ems_version_70", "deep_sleep_start_time_hour_min_1155"]
    entities = [
        registry.async_get_or_create(
            "sensor",
            "indevolt_modbus",
            f"{entry.entry_id}_{key}",
            config_entry=entry,
        )
        for key in keys
    ]
    unit.holding[70] = 10112
    unit.holding[1155] = 0x121E
    with patch(
        "custom_components.indevolt_modbus.async_get_unit", AsyncMock(return_value=unit)
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        await entry.runtime_data.async_refresh()
        for entity, expected, raw in zip(
            entities, ["V1.01.12", "18:30"], [10112, 0x121E], strict=True
        ):
            state = hass.states.get(entity.entity_id)
            assert state.state == expected
            assert state.attributes["raw_value"] == raw
            assert "unit_of_measurement" not in state.attributes
            assert "state_class" not in state.attributes
        unit.holding[1155] = 65535
        await entry.runtime_data.async_refresh()
        state = hass.states.get(entities[1].entity_id)
        assert state.state == "unknown"
        assert state.attributes["raw_value"] == 65535
        assert await hass.config_entries.async_unload(entry.entry_id)


def test_all_declared_formats_are_supported():
    for register in REGISTERS:
        if register.display_format:
            format_register_value(0, register.display_format)


async def test_every_register_can_be_exposed_together(hass, unit):
    """Exercise optional entities and HA's unit/state validation, without writes."""
    from custom_components.indevolt_modbus.const import (
        NUMBER_RANGES,
        SELECT_ADDRESSES,
        SWITCH_ADDRESSES,
    )

    unit.holding[7534] = 24
    unit.holding[7268] = 30
    unit.holding[7270] = 500
    unit.holding[7547] = [3, 4]
    unit.holding[122] = 990
    entry = MockConfigEntry(
        domain="indevolt_modbus",
        data={"host": "192.0.2.10", "port": 8899, "unit_id": 1},
    )
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    entities = {}
    for register in REGISTERS:
        domain = (
            "number"
            if register.address in NUMBER_RANGES
            else "select"
            if register.address in SELECT_ADDRESSES
            else "switch"
            if register.address in SWITCH_ADDRESSES
            else "sensor"
        )
        entities[register.address] = registry.async_get_or_create(
            domain,
            "indevolt_modbus",
            f"{entry.entry_id}_{register.key}",
            config_entry=entry,
        )
    with patch(
        "custom_components.indevolt_modbus.async_get_unit", AsyncMock(return_value=unit)
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        await entry.runtime_data.async_refresh()
        assert not entry.runtime_data.data.failed
        assert len(entry.runtime_data.data.updated) == len(REGISTERS)
        energy = hass.states.get(entities[7547].entity_id)
        assert energy.state == "196612"
        assert energy.attributes["device_class"] == "energy"
        assert energy.attributes["state_class"] == "total_increasing"
        assert energy.attributes["unit_of_measurement"] == "Wh"
        power_factor = hass.states.get(entities[122].entity_id)
        assert power_factor.state == "0.99"
        assert power_factor.attributes["device_class"] == "power_factor"
        assert power_factor.attributes["state_class"] == "measurement"
        assert power_factor.attributes.get("unit_of_measurement") is None
        for entity in entities.values():
            state = hass.states.get(entity.entity_id)
            assert state is not None
            assert state.state != "unavailable"
        for address, expected in [(7268, "d"), (7270, "W")]:
            state = hass.states.get(entities[address].entity_id)
            assert state.attributes["unit_of_measurement"] == expected
        for address, expected in [
            (118, "apparent_power"),
            (120, "reactive_power"),
            (1282, "duration"),
            (7600, "duration"),
        ]:
            state = hass.states.get(entities[address].entity_id)
            assert state.attributes["device_class"] == expected
        assert await hass.config_entries.async_unload(entry.entry_id)
