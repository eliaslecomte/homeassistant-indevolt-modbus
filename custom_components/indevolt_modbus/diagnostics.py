"""Provide diagnostics without network addresses or register values."""

from time import monotonic
from typing import Any

from homeassistant.core import HomeAssistant

from .coordinator import IndevoltConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: IndevoltConfigEntry
) -> dict[str, Any]:
    """Report supported and failed subsystems without identifying information."""
    coordinator = getattr(entry, "runtime_data", None)
    if coordinator is None or coordinator.data is None:
        return {"setup_complete": False, "state": entry.state.value}
    return {
        "polling": {
            "regular_interval": coordinator.regular_interval,
            "fast_battery_interval": coordinator.fast_interval,
            "message_spacing": coordinator.message_spacing,
            "read_duration_seconds_including_pacing": list(coordinator.read_durations),
            "age_seconds": {
                key: round(monotonic() - timestamp, 3)
                for key, timestamp in coordinator.last_success.items()
            },
        },
        "protocol_version": coordinator.device.protocol_version,
        "components": sorted(coordinator.device.components),
        "updated": sorted(coordinator.data.updated),
        "failed": {
            name: type(error).__name__
            for name, error in coordinator.data.failed.items()
        },
    }
