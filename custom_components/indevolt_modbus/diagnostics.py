"""Provide diagnostics without network addresses or register values."""

from typing import Any

from homeassistant.core import HomeAssistant

from .coordinator import IndevoltConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: IndevoltConfigEntry
) -> dict[str, Any]:
    """Report supported and failed subsystems without identifying information."""
    coordinator = entry.runtime_data
    return {
        "protocol_version": coordinator.device.protocol_version,
        "components": sorted(coordinator.device.components),
        "updated": sorted(coordinator.data.updated),
        "failed": {
            name: type(error).__name__
            for name, error in coordinator.data.failed.items()
        },
    }
