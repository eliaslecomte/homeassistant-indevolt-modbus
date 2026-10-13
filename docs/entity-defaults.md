# Configuration and diagnostic entity alignment

Reviewed on 2026-10-12 against the upstream HTTP integration at core commit
[`b34a2a5ef41a9f56856ab611299bdd27b79370f9`](https://github.com/home-assistant/core/tree/b34a2a5ef41a9f56856ab611299bdd27b79370f9/homeassistant/components/indevolt),
using its number, select, switch, sensor, binary-sensor and base-entity definitions.
HTTP key metadata comes from `indevolt-api==1.8.8`. Modbus meanings and units come
from the standalone library's `docs/registers.json` and generated typed fields;
see [sensor sources and mapping](sensor-defaults.md). The standalone library
remains independent of Home Assistant.

## Configuration controls

Core enables all four number controls, its energy-mode select and its three
switches by default. Modbus enables the following existing equivalents, retaining
its native codes, ranges, write behavior, entity domain and unique ID.

| Core entity | Core read / write key | Modbus entity / address | Mapping |
| --- | --- | --- | --- |
| Discharge limit | 6105 / 1142 | Number, 1142 | Backup SOC, %. Core's write definition explicitly identifies 1142; no off-grid backup SOC substitution. |
| Maximum AC output power | 11011 / 1147 | Number, 1147 | Maximum inverter discharge power, W. |
| Inverter input limit | 11009 / 1138 | Number, 1138 | AC charging power limit, W. |
| Feed-in power limit | 11010 / 1146 | Number, 1146 | Maximum grid feed-in power, W. |
| Energy mode | 7101 / 47005 | Select, 1144 | Self-consumption, realtime and scheduled operation. Modbus uses 1/4/6; HTTP uses 1/4/5. Existing firmware option gates still apply. |
| Grid charging | 2618 / 1143 | Switch, 1143 | Grid charging enable. HTTP read codes 1000/1001; Modbus 0/1. |
| Light | 7171 / 7265 | Select, 7265 | Front-panel LED strip, off/on plus half brightness in Modbus. Keep the select; do not add a duplicate switch. |
| Bypass | 680 / 7266 | Switch, 7266 | Off-grid/bypass enable, 0/1. |

The new default control sets are numbers `{1138, 1142, 1146, 1147}`, selects
`{1144, 7265}` and switches `{1143, 7266}`. Other Modbus controls remain disabled:
realtime command/power/target SOC, off-grid backup SOC, forced charging settings,
key-load enable and counter-current charge have no corresponding core control
entity. Core exposes realtime readback sensors, which are not duplicate Modbus
controls; their existence does not establish enabled defaults for control entities.

Core restricts its numbers and switches to hardware generation 2; its energy
select supports generations 1 and 2. Modbus currently has firmware gates but no
verified hardware-generation identity, so it cannot reproduce those generation
filters. The defaults apply to supported registers. A register can still be
unavailable on a particular device. No HTTP numeric range or generation number
is substituted for the Modbus protocol definitions.

Modbus retains `EntityCategory.CONFIG` for controls so they appear under
configuration. Core does not explicitly set a category on these controls.
Enabling a control entity only enables readback polling; it does not write or
change the device setting.

## Diagnostics

Every core diagnostic entity defaults to disabled. Modbus preserves that default
and marks equivalent readings diagnostic, retaining all existing sensor domains
and unique IDs, including readings core exposes as binary sensors.

| Core diagnostic family | Modbus counterpart | Default |
| --- | --- | --- |
| Main / sub / standalone operating role | Cluster mode 7241 (normal/master/slave), not system energy mode 1144 or cluster type 7242 | Disabled |
| Per-pack SOC | 7593–7598, master and five slaves; distinct from system SOC 7599 | Disabled |
| Per-pack voltage | 6010, 6122, 6234, 6346, 6458, 6733, V | Disabled |
| Per-pack current | 6108, 6220, 6332, 6444, 6556, 6831, A | Disabled |
| Per-pack cycle counts | 6008, 6120, 6232, 6344, 6456, 6731 | Disabled |
| Meter connected (core binary sensor) | Meter state 1246, existing enum sensor, disconnected/connected | Disabled |
| Per-pack heater states (core binary sensors) | 6593, 6625, 6657, 6689, 6721, 6865, existing enum/numeric sensors | Disabled |
| Temperatures | Existing Celsius readings are categorized diagnostic; see scope limits below | Disabled |

Existing info registers and event words remain diagnostic, except rated capacity
89: core treats total battery capacity as an ordinary enabled energy sensor, so
it is no longer categorized diagnostic. Full-system SOC, battery power and
battery charge/discharge state remain ordinary enabled measurements.

## Unmatched diagnostic scope

- Core's system equivalent-full-cycle count is not assumed to equal a single
  battery pack's cycle count. Only per-pack cycle-count categories are matched.
- Modbus minimum-cell temperatures and heater temperatures are useful diagnostics,
  but are not equivalent to core's unspecified pack temperature, MOS temperature,
  inverter temperature or transformer temperature. Categorizing them diagnostic
  does not change their native meaning, name or unit.
- Core battery serial-number readings have documented HTTP keys. The Modbus source
  lacks string lengths for 6022/6134/6246/6358/6470/6745, so they remain excluded;
  no strings, pack presence or pack hardware identities are inferred.
- Core generation-1 system heating state has no verified system-wide counterpart
  here; per-pack heating states are not substituted for it.
- Core filters slave-pack diagnostics by serial-number presence. Modbus cannot
  reproduce that filter without verified serial decoding, so supported pack
  registers remain optional, disabled entities.
- Existing Modbus firmware-version registers and alarm words have no core entity
  equivalents (core instead includes firmware in device metadata). Their current
  identities and disabled diagnostic defaults are retained.

## Existing installations and polling

Defaults apply when an entity-registry entry is first created. Existing enabled
entities stay enabled, and existing user-disabled or integration-disabled entities
stay disabled. Category changes can update the diagnostic/configuration grouping
without changing these choices. There is no registry migration, domain conversion,
new control or duplicate poller. An existing installation must manually enable
any of the newly default-enabled controls it wants to use.

A fresh V1.9 entry has 20 enabled entities (12 sensors, eight controls). Selective
polling now reads only these fields, using 18 contiguous requests (V1.7: 17), down
from the earlier whole-component totals of 56 and 52. Disabled sibling fields are
not read. Entity contexts are register keys, so battery power can run independently
of SOC. Adjacent selected fields within a component share one request.

Each group has its own deadline, and results are published immediately. Regular
polling defaults to 30 seconds after completion; fast battery polling is opt-in.
The shared scheduler prioritizes writes and their targeted readbacks, then fast
battery telemetry, while allowing regular work between fast reads. Actual intervals
depend on request spacing and device response time. See the README for settings,
freshness budgets, and diagnostics. Diagnostics themselves add no polling.

Tests verify default control sets, optional controls staying disabled, diagnostic
categories, stable identities, zero writes during setup, firmware gates,
component/read counts, and preservation of enabled and disabled choices across
unload/setup for all three control platforms and sensors.
