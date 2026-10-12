# Sensor defaults compared with the built-in HTTP integration

Reviewed on 2026-10-12 against the actual upstream Home Assistant HTTP
integration, not the local contribution draft used to maintain this Modbus
integration. The upstream sensor file's latest commit was
[`7e2343243d75c91c11c81828a962ac229cd79329`](https://github.com/home-assistant/core/blob/7e2343243d75c91c11c81828a962ac229cd79329/homeassistant/components/indevolt/sensor.py).
The current upstream manifest pins
[`indevolt-api==1.8.8`](https://pypi.org/project/indevolt-api/1.8.8/).
Its `indevolt_api/const.py` identifies the HTTP keys below. HTTP keys and Modbus
addresses belong to different protocols and must not be matched numerically.

Modbus meanings, units and scaling come from the independent library's
`docs/registers.json` and typed field definitions in `src/indevolt_modbus/components.py`.
The catalog records vendor source commit
`c073d8125cc8b35f926cf1198fe4697896b8d8cb` in `docs/sources.json`.
The vendor's [Modbus documentation](https://docs.indevolt.com/docs/hardware/open-data/modbus/)
is the protocol reference. No HA defaults or dependencies were added to that library.

## Confirmed sensor matches enabled for new entities

Upstream enables these sensors by default. Modbus retains its native units,
values, register keys and unique IDs; Wh versus kWh is a unit conversion, not a
reason to reject an otherwise equivalent energy measurement. Enum codes also
remain native to Modbus.

| Upstream sensor | HTTP key | Modbus address | Meaning and unit |
| --- | --- | --- | --- |
| Rated capacity | 142 | 89 | Combined system battery capacity; HTTP kWh, Modbus Wh |
| Battery power | 6000 | 6564 | Total battery charge/discharge power, W; Modbus positive discharge, negative charge |
| Battery charge/discharge state | 6001 | 6563 | Overall battery standby/charging/discharging; HTTP 1000/1001/1002, Modbus 0/1/2 |
| Battery SOC | 6002 | 7599 | Full-system SOC, %, Modbus scale 0.1 and protocol >= V1.8 |
| Battery daily charging energy | 6004 | 7519 | Daily battery charging; HTTP kWh, Modbus Wh |
| Battery daily discharging energy | 6005 | 7521 | Daily battery discharging; HTTP kWh, Modbus Wh |
| Battery total charging energy | 6006 | 1269 | Cumulative battery charging; HTTP kWh, Modbus Wh |
| Battery total discharging energy | 6007 | 1271 | Cumulative battery discharging; HTTP kWh, Modbus Wh |
| DC output power | 1501 | 2250 | Total PV charging/output power, W |
| Daily production | 1502 | 124 | Daily PV generation; HTTP kWh, Modbus Wh; `WH` is daily, not cumulative |
| Cumulative production | 1505 | 7512 | Cumulative PV generation, Wh |
| Bypass power | 667 | 7553 | Bypass power, W |

The enabled set is `{89, 124, 1269, 1271, 2250, 6563, 6564, 7512, 7519, 7521,
7553, 7599}`. Every other sensor defaults to disabled. Firmware gates still apply;
7599 is absent before V1.8, with no master-pack fallback because a pack's SOC is
not the full-system measurement.

## Upstream enabled sensors without a confirmed sensor match

| Upstream sensor | HTTP key | Candidate / decision |
| --- | --- | --- |
| Energy mode | 7101 | Modbus 1144 is already a select control; mode codes also differ. No duplicate sensor; see the subsequent control-default mapping. |
| Discharge limit (generation 1) | 6105 | Backup SOC controls 1142/1154 are candidates, but generation and on/off-grid semantics need confirmation. No sensor added. |
| Realtime command | 6107 | Modbus 1150 is already a select control; no duplicate sensor. |
| Realtime target SOC | 6108 | Modbus 1152 is already a number control; no duplicate sensor. |
| Realtime power limit | 6109 | Modbus 1151 is already a number control; no duplicate sensor. |
| AC input power | 2101 | 174 is signed inverter input/output power, not a separate input measurement. Leave disabled. |
| AC output power | 2108 | 1284 is combined net AC power (inverter plus bypass), not a separate output measurement; 174 is inverter-only signed power. Leave disabled. |
| Total AC input energy | 2107 | 170 is total inverter input energy; 7510 is inverter charging energy calculated from input power. System-total scope and duplicate-counter relationship are unconfirmed. Leave both disabled. |
| Total AC output energy | 2104 | 196 is bypass-port discharge energy; 7549 is daily on-grid output. Neither establishes cumulative system AC output. Leave disabled. |
| Off-grid output energy | 2105 | 7551 is daily inverter off-grid discharge, not a confirmed cumulative counterpart. Leave disabled. |
| Bypass input energy | 11034 | 7545 is microinverter generation energy; equivalence to all bypass input energy is unconfirmed. Leave disabled. |
| Meter power (generation 1/2) | 21028 / 11016 | 1247 explicitly measures phase U only; equivalence to upstream meter power across phases/models is unconfirmed. Leave disabled. |

The upstream realtime sensors are conditional on energy mode. Its generation
filters are hardware-generation filters, not the Modbus firmware-version gates.
No equivalence between those two schemes is assumed.

## Upstream disabled sensors and removed defaults

Upstream explicitly disables per-pack SOC (including main/master SOC), per-channel
PV current/voltage/power, temperatures, cycle counts, serial numbers, grid
voltage/frequency and remaining charge/discharge times. Their Modbus counterparts
remain disabled. Other unmatched Modbus diagnostics, events, settings, schedules
and load profiles also remain disabled.

Compared with the old defaults, add 89, 6563, 7519, 7521 and 7553; remove 174,
1284 and 7593. Master-pack SOC (7593) is distinct from system SOC (7599), so it is
not enabled as a substitute. The two removed AC power defaults have ambiguous
scope as described above.

## Sensor-only alignment in release 0.1.2

The following describes the sensor-only changes shipped in 0.1.2. Subsequent
[configuration and diagnostic alignment](entity-defaults.md) enables eight
control defaults and updates diagnostic categories; that document gives current
polling counts.

### Existing entities and polling impact

Only `entity_registry_enabled_default` changes. No entity-registry migration or
update is performed. Existing enabled entities stay enabled, and both user-disabled
and integration-disabled entities stay disabled across setup and reload. Users
can change their choices in entity settings. Entity identities and control
defaults are unchanged. There is still one coordinator per config entry.

For a fresh protocol V1.9 entry, defaults select seven components:
`battery_info`, `battery_real_time_data`, `battery_real_time_state`,
`battery_statistics`, `bypass_real_time_data`, `pv_real_time_data`, `pv_statistics`.
The real model with a mock transport issues 30 holding-register reads per cycle,
versus 23 for the previous seven-component set. Enabling rated capacity reads all
16 supported `battery_info` fields; multiple entities sharing a component do not
create additional polls. Protocol V1.7 issues 28 reads and does not create 7599.

With five seconds between requests and the default 30-second wait after a poll,
V1.9 takes
at least about 175 seconds between completed cycles before response time,
recovery retries and scheduling overhead (previously about 140 seconds). This is
an estimate from request count, not a hardware timing measurement. Existing
registry choices can produce different component sets and timings. This sensor-default change does not alter request spacing or the default
coordinator interval. A separately configured polling interval changes the wait
after each cycle.

Tests exercise new registry defaults and firmware gates, exact coordinator
contexts/read counts, all controls staying disabled, and preservation of
existing enabled and disabled choices through unload/setup.
