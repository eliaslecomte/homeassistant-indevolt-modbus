# Indevolt Modbus for Home Assistant

A local Modbus TCP integration for Indevolt storage devices, prepared for HACS
community testing. Requires **Home Assistant 2026.10.1 or newer** and HACS 2.0.5.
The standalone device library is included under
`custom_components/indevolt_modbus/vendor/indevolt_modbus`; no unpublished device
package is downloaded. The published `modbus-connection[tmodbus]` backend is
installed through the manifest.

## Installation

Publish this folder as the root of
[`eliaslecomte/homeassistant-indevolt-modbus`](https://github.com/eliaslecomte/homeassistant-indevolt-modbus).
In HACS, open **Custom repositories**, add that URL with category **Integration**, download
**Indevolt Modbus**, and restart Home Assistant. Alternatively copy
`custom_components/indevolt_modbus` into your configuration's `custom_components`.

Enable **Modbus server** in the Indevolt app, then go to **Settings → Devices &
services → Add integration → Indevolt Modbus**. Enter the device host, port **8899** and
unit **1**, unless you changed those values on the device. No YAML setup is
needed. This uses domain `indevolt_modbus`, separate from the built-in HTTP
integration's `indevolt` domain. Existing HTTP configuration is not migrated.
Avoid enabling competing controls against the same device while testing.

## Automatic discovery

For initial setup, Home Assistant can offer an Indevolt device advertising an
`igen_fw*` HTTP service over mDNS (`_http._tcp.local.`). Confirm the suggested
address and Modbus port/unit; setup checks Modbus only after you submit. The
HTTP service port is not used as the Modbus port. Manual setup remains available
when discovery is unavailable or you have more devices to add.

This uses the matcher from Home Assistant's built-in HTTP integration, as a
candidate address rather than proof of Modbus support. HTTP/OpenData may need
to be enabled as well as Modbus TCP, and mDNS must reach Home Assistant. No
device/firmware has yet been tested with this integration's discovery flow.
Because Modbus does not yet provide a verified hardware identity here, Home
Assistant's discovery-without-unique-ID helper offers only one initial flow,
suppresses discovery once an entry exists, and supports ignoring the suggestion.
It does not update addresses automatically or resolve hostname aliases.

See [discovery research](docs/discovery.md) for evidence and remaining limitations.

## What is included

- Power, battery SoC and energy sensors, plus optional diagnostic readings.
- Number controls for SoC and power limits; select controls for system,
  real-time and LED modes; switches for documented enable/disable settings.
- Firmware protocol gates, component-level availability and write readback.
- Reconfiguration, diagnostics, unload cleanup and tests on a real HA runtime.

New sensor and control defaults follow confirmed equivalents in the built-in HTTP
integration. Eight controls start enabled; diagnostic and other optional entities
start disabled. See the [sensor mapping](docs/sensor-defaults.md) and
[configuration/diagnostic mapping and polling impact](docs/entity-defaults.md).
English display names follow verified meanings while retaining original Modbus
identifiers. See the [original-to-display-name mapping](docs/display-names.md).
Existing entity settings are preserved. Enable the entities needed for your model
in their entity settings. Only enabled fields are polled; adjacent selected fields
within a subsystem share a request without reading undocumented gaps. Each result
is published immediately instead of waiting for a full cycle.

Under **Settings → Devices & services → Indevolt Modbus → Configure**:

| Setting | Default | Range | Meaning |
| --- | --- | --- | --- |
| Regular polling interval | 30 s | 5–3600 s | Wait after each regular register group's completed read |
| Fast-polled sensor | ACOutW for new setups | Enabled sensors on this device, or Disabled | Select one sensor for fast polling; Disabled puts everything on regular polling |
| Fast polling interval (advanced) | 3 s | 1–3600 s | Target completion cadence for the selected sensor |
| Minimum spacing between requests | 2 s | 1–60 s | Shared pacing for reads and writes |

Fast polling uses the selected existing sensor; it does not create a duplicate.
The dropdown lists enabled sensors belonging to this device. ACOutW (1284), which
includes inverter and bypass power, is the default for new setups and is enabled
by default for newly created entities. Inverter AC power (174) is useful for
control feedback. Choose **Disabled** (stored as an empty selection) to turn fast
polling off. Enable a disabled sensor in the entity list before selecting it.

Existing installations retain their previous enabled/disabled state and interval:
legacy enabled fast polling selects Inverter AC power. Existing entity enablement
choices are preserved. A saved selection that becomes disabled stays visible but
is not polled until re-enabled. Entity renames are safe because the selection is
stored as a stable register key. Other sensors use regular polling.

Expand **Advanced polling** to adjust the fast interval. Selecting
a sensor uses three seconds unless a positive interval was previously saved.
Saving reloads the integration; regular interval and request spacing are preserved.

All intervals are best-effort targets. One worker serializes operations, prioritizes
writes plus their targeted readbacks, and interleaves fast reads with regular work.
The scheduler reserves the next selected sensor slot using an adaptive response-time estimate
and skips missed slots without catch-up bursts. At least one due regular request
gets a turn between fast reads. Writes remain highest priority. Response time,
pacing, connection recovery, and writes can extend the observed interval. A 2-second
fast target with 5-second pacing cannot produce 2-second updates. The manufacturer
recommends at least 5 seconds between requests and supports a minimum of 1 second;
The 2-second default is an experiment to stay below the approximately 5-second
idle connection closures observed during profiling; hardware behavior may vary. Changing a setting no longer requests a
full telemetry refresh. Writes are never automatically replayed.

Failures affect only the fields in that request and are retried with backoff.
Values older than the greater of three polling intervals or four times
(request spacing + 2 seconds) are treated as stale. Diagnostics include field ages
and the last 100 read durations **including pacing and recovery**, not just wire
response latency. Default V1.9 entities require 18 reads instead of 56 (V1.7: 17
instead of 52). The priority scheduler and faster pacing still need live validation.

The new core Modbus API is used automatically when present. On 2026.10.1, which
does not expose that API, this integration owns its connection and closes it on
unload, failed setup and shutdown. On that fallback, avoid another integration
or application polling the same device simultaneously. Separate fallback
entries do not share connections. Physical RTU is not exposed while vendor
support remains forthcoming.

## Community test status and known limits

Automated tests cover decoding, writes, config flow, polling, reconfiguration
and cleanup. Read-only setup and polling have been tested on a CMS-SF2000 with protocol V2.4.
Other models and device controls still need hardware testing. Consult the vendor's
[firmware and device table](https://docs.indevolt.com/docs/hardware/open-data/modbus/)
before testing. This integration cannot confirm product model or hardware
identity: the register source omits string lengths. Entry IDs keep entity IDs
stable during reconfiguration; duplicate host/port/unit combinations are
rejected, but hostname aliases cannot be recognized as the same device.

Alarm words remain numeric. The source labels register 7592 as voltage despite
Hz units; the standalone catalog preserves the inconsistency. Multiword values
use big-endian words pending hardware verification. No undocumented sentinels
are assumed. Real-time commands are capped at the documented single-unit
3600 W. Packed schedules and load profiles are library APIs, not UI controls.

Download diagnostics from the integration menu for compatibility reports.
Include the exact device model, firmware, protocol version and observed issue.
Remove identifying details from logs or raw captures before posting them.
Remove this integration through **Settings → Devices & services**, then remove
it from HACS and restart if you no longer need it.

## Development and releases

This repository follows the
[integration blueprint](https://github.com/ludeeus/integration_blueprint):
HACS metadata, devcontainer, setup/develop/lint helpers, issue template, Ruff,
hassfest and HACS validation workflows. Apache licensing for the vendored
library is preserved separately from the integration template's MIT license.

```sh
scripts/setup
scripts/lint
pytest -q
scripts/develop
```

In the original three-folder workspace, run `python scripts/sync.py` to copy
core changes and refresh the vendored library, then run Ruff and the tests.
Do not change the vendored package directly. It is copied without import-path
rewrites; relative imports keep it isolated from installed device packages.

Repository metadata is configured for `eliaslecomte/homeassistant-indevolt-modbus`,
with `@eliaslecomte` as codeowner. Before a GitHub release, run both validation
workflows. To change repository ownership later, run
`python scripts/configure_repository.py OWNER REPOSITORY`. HACS validation includes
the bundled brand images.
Tag releases to match `custom_components/indevolt_modbus/manifest.json`. HACS can install the repository directly; no zip release is required.

## Brand images

The integration bundles Indevolt icons and logos in `brand/`, with light/dark
and standard/high-resolution variants. Home Assistant serves these locally;
local brand images are supported since Home Assistant 2026.3.

These images are unchanged copies of the existing Indevolt assets from the
[Home Assistant brands repository](https://github.com/home-assistant/brands/tree/ba54a5eb87172d6f20b74741e4a96335f94cbd1c/core_integrations/indevolt).
Product names, trademarks and logos remain the property of their respective
owners. They identify supported devices and do not imply manufacturer endorsement.
The integration's MIT license does not relicense these trademarks or images.

### Idle connection recovery

Some device firmware closes TCP connections around the five-second request
interval. A disconnected holding-register read is retried once after waiting
for the pacing interval, allowing the backend to reconnect immediately before
sending. Writes are never replayed automatically.

With 2-second spacing, a 5-second inverter AC power target leaves limited capacity for
regular telemetry. A 90–120-second regular interval is a reasonable starting
point for the current enabled workload; the default remains 30 seconds.
Diagnostics expose per-group successful-poll gaps, fast completion lateness,
explicit-job queue waits, failure counts and connection-loss counts since start.
The response-time estimate is scheduling feedback, not measured wire latency.

### Fast polling target and power direction

Fast polling and freshness checks follow the sensor selected in options.
Diagnostics report `fast_poll_sensor` (stable register key, empty when disabled)
and `fast_poll_interval` (effective interval, zero when disabled). These replace
`fast_ac_power_interval`; historical profiling documents describe earlier targets.
Existing entity IDs and unique IDs are retained.

Register 174 is positive for AC charging/input and negative for discharging/output.
Battery power (6564) uses the opposite convention: positive discharge, negative
charge. Neither value is sign-inverted. Total inverter-plus-bypass AC power
(ACOutW, 1284) now decodes as signed int16: raw 63609 becomes -1927 W.
The vendor's uint16 type conflicts with its directional description; the
[canonical library documentation](https://github.com/eliaslecomte/indevolt-modbus#directional-ac-power-correction) records the correction.
