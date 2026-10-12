"""English presentation must preserve protocol tokens and registry identity."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.translation import async_get_translations
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.indevolt_modbus.vendor.indevolt_modbus import REGISTERS

DOMAIN = "indevolt_modbus"
ROOT = Path(__file__).resolve().parents[1]
REGISTERS_BY_KEY = {r.key: r for r in REGISTERS}


def test_translation_catalog_integrity():
    """All display entries retain catalog keys and native enum codes."""
    integration = ROOT / "custom_components" / DOMAIN
    strings = json.loads((integration / "strings.json").read_text())
    assert strings == json.loads((integration / "translations/en.json").read_text())
    for entities in strings["entity"].values():
        for key, translation in entities.items():
            register = REGISTERS_BY_KEY[key]
            assert translation["name"].strip()
            if "state" in translation:
                assert set(translation["state"]) == {
                    str(code) for code in register.options
                }


async def test_english_translations_load(hass):
    """HA resolves names and enum labels without changing the option tokens."""
    translations = await async_get_translations(hass, "en", "entity", {DOMAIN})
    prefix = f"component.{DOMAIN}.entity"
    assert translations[f"{prefix}.sensor.wh_124.name"] == "Daily production"
    assert translations[f"{prefix}.sensor.grid_voltage_7592.name"] == "Grid frequency"
    assert translations[f"{prefix}.select.system_mode_1144.state.6"] == (
        "Charge/discharge schedule"
    )
    assert translations[f"{prefix}.select.realtime_control_order_1150.state.0"] == (
        "Default"
    )
    assert translations[f"{prefix}.select.realtime_control_order_1150.state.2"] == (
        "Discharge"
    )


@pytest.mark.parametrize(
    ("platform", "key", "old_name", "new_name"),
    [
        ("sensor", "wh_124", "WH", "Daily production"),
        ("number", "back_up_soc_1142", "BackUpSoc", "Discharge limit"),
        ("select", "system_mode_1144", "SystemMode", "Energy mode"),
        (
            "switch",
            "grid_charge_enable_1143",
            "GridChargeEnable",
            "Allow grid charging",
        ),
    ],
)
@pytest.mark.parametrize("custom_name", [None, "My chosen name"])
async def test_existing_names_and_ids_survive(
    hass, unit, platform, key, old_name, new_name, custom_name
):
    """Refresh only original_name on setup/reload, preserving user settings."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Indevolt",
        data={"host": "192.0.2.10", "port": 8899, "unit_id": 1},
    )
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    unique_id = f"{entry.entry_id}_{key}"
    original = registry.async_get_or_create(
        platform,
        DOMAIN,
        unique_id,
        config_entry=entry,
        suggested_object_id="existing_technical_name",
        original_name=old_name,
    )
    registry.async_update_entity(
        original.entity_id,
        name=custom_name,
        icon="mdi:star",
        hidden_by=er.RegistryEntryHider.USER,
    )
    with patch(
        f"custom_components.{DOMAIN}.async_get_unit", AsyncMock(return_value=unit)
    ):
        for _ in range(2):
            assert await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()
            current = registry.async_get(original.entity_id)
            assert current.unique_id == unique_id
            assert current.original_name == new_name
            assert current.name == custom_name
            assert current.icon == "mdi:star"
            assert current.hidden_by is er.RegistryEntryHider.USER
            assert current.disabled_by is None
            await entry.runtime_data.async_refresh()
            await hass.async_block_till_done()
            state = hass.states.get(original.entity_id)
            assert state.attributes["friendly_name"] == (
                custom_name or f"Indevolt {new_name}"
            )
            if platform == "select":
                assert state.state == "1"
                assert state.attributes["options"] == ["1", "4", "6"]
            assert await hass.config_entries.async_unload(entry.entry_id)
