"""Core-equivalent diagnostics and persisted control defaults."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import EntityCategory
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.indevolt_modbus.vendor.indevolt_modbus import REGISTERS

DOMAIN = "indevolt_modbus"
PREFIX = "custom_components.indevolt_modbus"
DATA = {"host": "192.0.2.10", "port": 8899, "unit_id": 1}


async def test_diagnostic_categories_and_identity(hass, unit):
    """Categorize established registers without new entities or binary duplicates."""
    entry = MockConfigEntry(domain=DOMAIN, data=DATA)
    entry.add_to_hass(hass)
    with patch(f"{PREFIX}.async_get_unit", AsyncMock(return_value=unit)):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        registry = er.async_get(hass)
        entities = er.async_entries_for_config_entry(registry, entry.entry_id)
        by_key = {r.key: r for r in REGISTERS}
        diagnostic = {
            1246,
            7241,
            6008,
            6120,
            6232,
            6344,
            6456,
            6731,
            6010,
            6122,
            6234,
            6346,
            6458,
            6733,
            6108,
            6220,
            6332,
            6444,
            6556,
            6831,
            6593,
            6625,
            6657,
            6689,
            6721,
            6865,
            7593,
            7594,
            7595,
            7596,
            7597,
            7598,
        }
        found = set()
        for entity in entities:
            register = by_key[entity.unique_id.removeprefix(f"{entry.entry_id}_")]
            if register.address in diagnostic or register.unit == "°C":
                found.add(register.address)
                assert entity.domain == "sensor"
                assert entity.entity_category is EntityCategory.DIAGNOSTIC
                assert entity.disabled_by is er.RegistryEntryDisabler.INTEGRATION
            if register.address in {89, 6563, 6564, 7599}:
                assert entity.entity_category is None
                assert entity.disabled_by is None
        assert diagnostic <= found
        assert not hass.states.async_all("binary_sensor")
        assert len(entities) == len(entry.runtime_data.device.registers)
        assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.parametrize(
    ("domain", "address", "optional_address"),
    [("number", 1138, 1151), ("select", 1144, 1150), ("switch", 1143, 7272)],
)
@pytest.mark.parametrize(
    "disabled_by", [er.RegistryEntryDisabler.USER, er.RegistryEntryDisabler.INTEGRATION]
)
async def test_control_registry_choices_survive(
    hass, unit, domain, address, optional_address, disabled_by
):
    """Existing disabled defaults and enabled optional controls retain choices."""
    entry = MockConfigEntry(domain=DOMAIN, data=DATA)
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    registers = {r.address: r for r in REGISTERS}
    default = registry.async_get_or_create(
        domain,
        DOMAIN,
        f"{entry.entry_id}_{registers[address].key}",
        config_entry=entry,
        disabled_by=disabled_by,
    )
    optional = registry.async_get_or_create(
        domain,
        DOMAIN,
        f"{entry.entry_id}_{registers[optional_address].key}",
        config_entry=entry,
    )
    with patch(f"{PREFIX}.async_get_unit", AsyncMock(return_value=unit)):
        for _ in range(2):
            assert await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()
            assert registry.async_get(default.entity_id).disabled_by is disabled_by
            assert registry.async_get(optional.entity_id).disabled_by is None
            assert (
                registry.async_get(default.entity_id).entity_category
                is EntityCategory.CONFIG
            )
            assert await hass.config_entries.async_unload(entry.entry_id)
