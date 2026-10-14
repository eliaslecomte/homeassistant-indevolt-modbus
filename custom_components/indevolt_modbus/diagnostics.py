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
            "disconnect_count_since_start": coordinator.disconnect_count,
            "selected_group_count": len(coordinator._groups),
            "explicit_job_queue_wait_seconds": list(coordinator.job_queue_waits),
            "pending_writes": len(coordinator._writes),
            "pending_refresh_reads": len(coordinator._reads),
            "response_estimate_seconds_not_wire": coordinator._response_estimate,
            "groups": [
                {
                    "fields": sorted(group.reader.resolved_fields),
                    "fast": group.fast,
                    "successes": group.successes,
                    "failures": group.errors,
                    "successful_poll_gaps_seconds": list(group.gaps),
                    "completion_lateness_seconds": list(group.lateness),
                }
                for group in coordinator._groups
            ],
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
