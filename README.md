# Indevolt Modbus for Home Assistant

A local Modbus TCP integration for Indevolt storage devices, prepared for HACS
community testing. Requires **Home Assistant 2026.10.1 or newer** and HACS 2.0.5.
The standalone device library
[`indevolt-modbus==0.1.0`](https://pypi.org/project/indevolt-modbus/0.1.0/)
and its Modbus backend are installed through the manifest.

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

Polling uses fixed intervals:

| Data | Target |
| --- | --- |
| Total AC power (ACOutW, register 1284) | 10-second completion cadence |
| Other live telemetry, counters, events and device clock | 60 seconds after each read group completes |
| Settings and operating modes | 5 minutes after each read group completes |
| Device information (catalog Info fields) | 1 hour after each read group completes |
| Minimum spacing between requests | 2 seconds |

ACOutW includes inverter and bypass power. Its schedule follows the stable
register key, so renaming `sensor.indevolt_acoutw` does not affect polling.
Disabled entities are not polled. There are no polling configuration options;
upgrading removes the previous timing options and applies these fixed intervals.
Existing entity IDs and enablement choices are preserved.

All enabled fields receive an initial read regardless of tier. Explicit manual
refreshes include settings and information. Writes immediately read back the
changed field, without waiting for the next five-minute poll. Changes made through
the Indevolt app or another client can take up to the next settings poll to appear.
Information is not assumed immutable: firmware versions, rated capacity and hardware
capabilities are checked hourly. The Modbus protocol version used to select supported
registers is detected during setup; discovering new register support after a firmware
change requires reloading the integration. Writable clock words 1132–1134 remain
on the 60-second telemetry tier rather than the settings tier.

One worker serializes reads, writes and targeted readbacks. It reserves the next
ACOutW slot using an adaptive response-time estimate and anchors subsequent slots
to the original cadence instead of waiting another 10 seconds after each response.
Missed slots are skipped without catch-up bursts. Due regular requests get a turn
between ACOutW reads, and writes remain highest priority. An early manual refresh
preserves the next ACOutW slot when request spacing permits it.

The intervals are targets: slow responses, retries, writes and a large enabled
entity set can delay them. In particular, 60 seconds is not a guarantee that all
telemetry fields can be read within one 60-second window. The manufacturer recommends
5-second request spacing and supports a minimum of 1 second; this integration
retains the 2-second spacing used during hardware profiling.

Home Assistant's **Enable polling for updates** system option controls automatic
reads. When it is disabled, explicit `homeassistant.update_entity` refreshes and
control writes with their readbacks still work. Removing the last enabled entity
listener pauses automatic reads. The worker is tied to the config entry and is
cancelled on unload or Home Assistant shutdown. Control writes never trigger a
full telemetry refresh and are never automatically replayed.

Failures affect only the fields in that request and are retried with backoff.
Values older than the greater of three polling intervals or four times
(request spacing + 2 seconds) are treated as stale. Diagnostics include field ages
and the last 100 read durations **including pacing and recovery**, not just wire
response latency. Default V1.9 entities require 18 reads instead of 56 (V1.7: 17
instead of 52). The tiered schedule is checked with simulated request pacing; live results depend
on the device and enabled workload.

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
hassfest and HACS validation workflows. The standalone library is distributed
under Apache-2.0 separately from the integration template's MIT license.

```sh
scripts/setup
scripts/lint
pytest -q
scripts/develop
```

In the original three-folder workspace, run `python scripts/sync.py` to copy
core changes, then run Ruff and the tests. The integration imports the published
library directly; update its pinned version in both the manifest and
`requirements_common.txt` when adopting a new library release.

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

Diagnostics expose per-group successful-poll gaps, fast completion lateness,
explicit-job queue waits, failure counts and connection-loss counts since start.
The response-time estimate is scheduling feedback, not measured wire latency.

### Fast polling target and power direction

ACOutW has a fixed 10-second target; telemetry uses 60 seconds, settings use
300 seconds, and information uses 3600 seconds.
Diagnostics report `fast_poll_sensor` as `acout_w_1284` and
`fast_poll_interval` as `10`, alongside `settings_interval`, `info_interval`
and each read group's `interval`. These describe the internal schedule, not user
options. Historical profiling documents describe earlier configurable targets.
Existing entity IDs and unique IDs are retained.

Register 174 is positive for AC charging/input and negative for discharging/output.
Battery power (6564) uses the opposite convention: positive discharge, negative
charge. Neither value is sign-inverted. Total inverter-plus-bypass AC power
(ACOutW, 1284) now decodes as signed int16: raw 63609 becomes -1927 W.
The vendor's uint16 type conflicts with its directional description; the
[canonical library documentation](https://github.com/eliaslecomte/indevolt-modbus#directional-ac-power-correction) records the correction.
## Register display formats

Firmware and protocol versions use their documented `V…` notation. Packed
schedule/sleep times display as `HH:MM`; split device clock fields display their
individual year/month, day/hour, or minute/second values. These text sensors keep
the original numeric value in a `raw_value` attribute. Invalid packed clock
values display as unknown instead of an impossible time. Entity IDs are unchanged.

Forced-full-charge interval uses days (`d`); forced AC charging power uses watts.
Apparent power, reactive power, and durations have their corresponding Home
Assistant device classes. Enum states retain stable numeric codes and translated
UI labels. Unknown codes and device-rejected reads are not replaced with zero.

The daily microinverter energy counter (7547) is decoded as a two-register Wh
counter. Stray OFF/ON continuation rows in the vendor table are excluded from
its enum metadata; they would otherwise truncate the read and lose the unit.

Inverter power factor is a unitless ratio (for example `0.99`), with HA's
power-factor device class. The vendor's `Pct` label conflicts with its 0.001
scale and observed readings; the numerical value and sign are preserved.
