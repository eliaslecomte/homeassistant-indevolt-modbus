"""Sensor defaults, persisted registry choices and resulting polling."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import EntityCategory
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.indevolt_modbus.vendor.indevolt_modbus import REGISTERS

DOMAIN = "indevolt_modbus"
PREFIX = "custom_components.indevolt_modbus"
EXPECTED_SENSORS = {
    1284,
    89,
    124,
    1269,
    1271,
    2250,
    6563,
    6564,
    7512,
    7519,
    7521,
    7553,
    7599,
}
EXPECTED_CONTROLS = {
    "number": {1138, 1142, 1146, 1147},
    "select": {1144, 7265},
    "switch": {1143, 7266},
}
EXPECTED = EXPECTED_SENSORS | set().union(*EXPECTED_CONTROLS.values())


@pytest.mark.parametrize("version", [17, 19])
async def test_new_entity_defaults_and_polling(hass, unit, version):
    """Only semantic matches start enabled, with protocol gates still applied."""
    unit.holding[7534] = version
    writes = []
    unit.on_write(writes.append)
    entry = MockConfigEntry(
        domain=DOMAIN, data={"host": "192.0.2.10", "port": 8899, "unit_id": 1}
    )
    entry.add_to_hass(hass)
    with patch(f"{PREFIX}.async_get_unit", AsyncMock(return_value=unit)):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        registry = er.async_get(hass)
        entities = er.async_entries_for_config_entry(registry, entry.entry_id)
        enabled = {e.unique_id for e in entities if e.disabled_by is None}
        expected_registers = [
            r
            for r in REGISTERS
            if r.address in EXPECTED and r.minimum_version <= version
        ]
        assert enabled == {f"{entry.entry_id}_{r.key}" for r in expected_registers}
        by_key = {r.key: r for r in REGISTERS}
        for entity in entities:
            register = by_key[entity.unique_id.removeprefix(f"{entry.entry_id}_")]
            if entity.domain in EXPECTED_CONTROLS:
                assert entity.entity_category is EntityCategory.CONFIG
                assert (entity.disabled_by is None) == (
                    register.address in EXPECTED_CONTROLS[entity.domain]
                )
        assert not writes
        coordinator = entry.runtime_data
        components = {r.key for r in expected_registers}
        assert set(coordinator.async_contexts()) == components
        unit.read_events.clear()
        await coordinator.async_refresh()
        assert coordinator.data.updated == components
        # Only enabled fields are read; adjacent selected fields share a request.
        assert len(unit.read_events) == (18 if version == 17 else 19)
        assert coordinator.regular_interval == 30
        assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.parametrize(
    "disabled_by", [er.RegistryEntryDisabler.USER, er.RegistryEntryDisabler.INTEGRATION]
)
async def test_existing_registry_choices_survive(hass, unit, disabled_by):
    """A newly enabled default stays disabled; an old enabled default stays on."""
    entry = MockConfigEntry(
        domain=DOMAIN, data={"host": "192.0.2.10", "port": 8899, "unit_id": 1}
    )
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    registers = {r.address: r for r in REGISTERS}
    capacity = registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_{registers[89].key}",
        config_entry=entry,
        disabled_by=disabled_by,
    )
    pack_soc = registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_{registers[7593].key}",
        config_entry=entry,
    )
    with patch(f"{PREFIX}.async_get_unit", AsyncMock(return_value=unit)):
        for _ in range(2):
            assert await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()
            assert registry.async_get(capacity.entity_id).disabled_by is disabled_by
            assert registry.async_get(pack_soc.entity_id).disabled_by is None
            assert (
                registry.async_get(pack_soc.entity_id).entity_category
                is EntityCategory.DIAGNOSTIC
            )
            assert registers[89].key not in set(entry.runtime_data.async_contexts())
            assert registers[7593].key in set(entry.runtime_data.async_contexts())
            assert await hass.config_entries.async_unload(entry.entry_id)
