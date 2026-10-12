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

## What is included

- Power, battery SoC and energy sensors, plus optional diagnostic readings.
- Number controls for SoC and power limits; select controls for system,
  real-time and LED modes; switches for documented enable/disable settings.
- Firmware protocol gates, component-level availability and write readback.
- Reconfiguration, diagnostics, unload cleanup and tests on a real HA runtime.

Most entities and every control start disabled. Enable the ones needed for your
model in the entity settings. Only enabled entities' components are polled.
Requests are spaced by five seconds; each poll is followed by a 30-second wait.
Many enabled entities can therefore make updates take several minutes.

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
Tag releases to match `custom_components/indevolt_modbus/manifest.json` (initially
`0.1.0`). HACS can install the repository directly; no zip release is required.

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
