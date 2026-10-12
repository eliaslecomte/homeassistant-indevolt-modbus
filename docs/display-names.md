# English display names

Reviewed 2026-10-12 against the actual upstream HTTP integration's
[strings.json at c4bb96f5793c23be2467c49091fb3289313ab954](https://github.com/home-assistant/core/blob/c4bb96f5793c23be2467c49091fb3289313ab954/homeassistant/components/indevolt/strings.json).
See [sensor mapping](sensor-defaults.md) and [control/diagnostic mapping](entity-defaults.md)
for semantic evidence, protocol differences and scope limits. Additional names
use the descriptions in the standalone library's `docs/registers.json`.
Home Assistant names use sentence case, retain acronyms and omit units already
provided by entity metadata.

Only English presentation changes. Register names, keys, addresses, translation
keys, enum codes, unique IDs, units, firmware gates, defaults and polling are
unchanged. Existing entity IDs, user names and registry choices are preserved;
new entities may receive IDs based on their clearer display names. No registry
migration is performed. Enum labels are presentation only; automations and
service calls continue to use the same numeric strings.

The authoritative translation source is the sibling local core draft's
`homeassistant/components/indevolt/strings.json`. `scripts/sync.py` copies it to
the custom integration and `translations/en.json`. The standalone library has
no Home Assistant presentation dependencies. Original names remain available
in its catalog and the vendored `Register.name`, and every changed name is mapped
below (including unchanged technical keys).

## Name mapping

“Upstream equivalent” uses the verified HTTP label, not its register number or
codes. Main means the master battery pack; packs 1–5 mean the corresponding
slave packs. Minimum-cell temperatures are intentionally more specific than
the HTTP pack-temperature labels. Register 7592's original “Grid voltage” is a
catalog naming error: its description and Hz unit establish grid frequency.

| Platform | Address | Original Modbus name | Display name | Translation key (unchanged) | Basis |
| --- | --- | --- | --- | --- | --- |
| sensor | 70 | EMS Version | EMS version | `ems_version_70` | Modbus description; scope retained |
| sensor | 71 | BMS Master Version | Main BMS version | `bms_master_version_71` | Modbus description; scope retained |
| sensor | 72 | Inverter Version | Inverter version | `inverter_version_72` | Modbus description; scope retained |
| sensor | 73 | MPPT Version | MPPT version | `mppt_version_73` | Modbus description; scope retained |
| sensor | 78 | Maximum MPPT Channels | Maximum MPPT channels | `maximum_mppt_channels_78` | Modbus description; scope retained |
| sensor | 89 | Rated Capacity（Wh） | Rated capacity | `rated_capacity_wh_89` | Upstream equivalent |
| sensor | 103 | AphA | Inverter AC current | `aph_a_103` | Modbus description; scope retained |
| sensor | 110 | PhVphA | Inverter AC voltage | `ph_vph_a_110` | Modbus description; scope retained |
| sensor | 116 | Hz | Inverter AC frequency | `hz_116` | Modbus description; scope retained |
| sensor | 118 | VA | Inverter AC apparent output power | `va_118` | Modbus description; scope retained |
| sensor | 120 | VAr | AC reactive power | `var_120` | Modbus description; scope retained |
| sensor | 122 | PF | Inverter AC output power factor | `pf_122` | Modbus description; scope retained |
| sensor | 124 | WH | Daily production | `wh_124` | Upstream equivalent |
| sensor | 138 | St | System operating status | `st_138` | Modbus description; scope retained |
| sensor | 154 | HomeUseW | Home load power | `home_use_w_154` | Modbus description; scope retained |
| sensor | 1246 | MeterState | Meter connection state | `meter_state_1246` | Modbus description; scope retained |
| sensor | 1247 | MeterPu | Meter phase U power | `meter_pu_1247` | Modbus description; scope retained |
| sensor | 1269 | B Charge Energy | Battery total charging energy | `b_charge_energy_1269` | Upstream equivalent |
| sensor | 1271 | B disCharge Energy | Battery total discharging energy | `b_dis_charge_energy_1271` | Upstream equivalent |
| sensor | 1282 | ChargeLeftTime | Remaining charging time | `charge_left_time_1282` | Upstream equivalent |
| sensor | 1283 | DischargeLeftTime | Remaining discharging time | `discharge_left_time_1283` | Upstream equivalent |
| sensor | 2219 | DCA | DC input current 1 | `dca_2219` | Upstream equivalent |
| sensor | 2220 | DCV | DC input voltage 1 | `dcv_2220` | Upstream equivalent |
| sensor | 2221 | DCW | DC input power 1 | `dcw_2221` | Upstream equivalent |
| sensor | 2239 | DCA | DC input current 2 | `dca_2239` | Upstream equivalent |
| sensor | 2240 | DCV | DC input voltage 2 | `dcv_2240` | Upstream equivalent |
| sensor | 2241 | DCW | DC input power 2 | `dcw_2241` | Upstream equivalent |
| sensor | 2250 | PV total power | DC output power | `pv_total_power_2250` | Upstream equivalent |
| sensor | 2260 | DCA | DC input current 3 | `dca_2260` | Upstream equivalent |
| sensor | 2261 | DCV | DC input voltage 3 | `dcv_2261` | Upstream equivalent |
| sensor | 2262 | DCW | DC input power 3 | `dcw_2262` | Upstream equivalent |
| sensor | 2280 | DCA | DC input current 4 | `dca_2280` | Upstream equivalent |
| sensor | 2281 | DCV | DC input voltage 4 | `dcv_2281` | Upstream equivalent |
| sensor | 2282 | DCW | DC input power 4 | `dcw_2282` | Upstream equivalent |
| sensor | 6008 | NCyc | Main cycles | `ncyc_6008` | Upstream equivalent |
| sensor | 6010 | V | Main voltage | `v_6010` | Upstream equivalent |
| sensor | 6018 | CellTmpMin | Main battery minimum cell temperature | `cell_tmp_min_6018` | Modbus minimum-cell scope; not upstream pack temperature |
| sensor | 6108 | A | Main current | `a_6108` | Upstream equivalent |
| sensor | 6120 | NCyc | Battery pack 1 cycles | `ncyc_6120` | Upstream equivalent |
| sensor | 6122 | V | Battery pack 1 voltage | `v_6122` | Upstream equivalent |
| sensor | 6130 | CellTmpMin | Battery pack 1 minimum cell temperature | `cell_tmp_min_6130` | Modbus minimum-cell scope; not upstream pack temperature |
| sensor | 6220 | A | Battery pack 1 current | `a_6220` | Upstream equivalent |
| sensor | 6232 | NCyc | Battery pack 2 cycles | `ncyc_6232` | Upstream equivalent |
| sensor | 6234 | V | Battery pack 2 voltage | `v_6234` | Upstream equivalent |
| sensor | 6242 | CellTmpMin | Battery pack 2 minimum cell temperature | `cell_tmp_min_6242` | Modbus minimum-cell scope; not upstream pack temperature |
| sensor | 6332 | A | Battery pack 2 current | `a_6332` | Upstream equivalent |
| sensor | 6344 | NCyc | Battery pack 3 cycles | `ncyc_6344` | Upstream equivalent |
| sensor | 6346 | V | Battery pack 3 voltage | `v_6346` | Upstream equivalent |
| sensor | 6354 | CellTmpMin | Battery pack 3 minimum cell temperature | `cell_tmp_min_6354` | Modbus minimum-cell scope; not upstream pack temperature |
| sensor | 6444 | A | Battery pack 3 current | `a_6444` | Upstream equivalent |
| sensor | 6456 | NCyc | Battery pack 4 cycles | `ncyc_6456` | Upstream equivalent |
| sensor | 6458 | V | Battery pack 4 voltage | `v_6458` | Upstream equivalent |
| sensor | 6466 | CellTmpMin | Battery pack 4 minimum cell temperature | `cell_tmp_min_6466` | Modbus minimum-cell scope; not upstream pack temperature |
| sensor | 6556 | A | Battery pack 4 current | `a_6556` | Upstream equivalent |
| sensor | 6563 | BatteryState | Battery charge/discharge state | `battery_state_6563` | Upstream equivalent |
| sensor | 6564 | BatteryPower | Battery power | `battery_power_6564` | Upstream equivalent |
| sensor | 6593 | electric heating state | Main electric heating state | `electric_heating_state_6593` | Modbus per-pack state; sensor domain retained |
| sensor | 6625 | electric heating state | Battery pack 1 electric heating state | `electric_heating_state_6625` | Modbus per-pack state; sensor domain retained |
| sensor | 6657 | electric heating state | Battery pack 2 electric heating state | `electric_heating_state_6657` | Modbus per-pack state; sensor domain retained |
| sensor | 6689 | electric heating state | Battery pack 3 electric heating state | `electric_heating_state_6689` | Modbus per-pack state; sensor domain retained |
| sensor | 6721 | electric heating state | Battery pack 4 electric heating state | `electric_heating_state_6721` | Modbus per-pack state; sensor domain retained |
| sensor | 6731 | NCyc | Battery pack 5 cycles | `ncyc_6731` | Upstream equivalent |
| sensor | 6733 | V | Battery pack 5 voltage | `v_6733` | Upstream equivalent |
| sensor | 6741 | CellTmpMin | Battery pack 5 minimum cell temperature | `cell_tmp_min_6741` | Modbus minimum-cell scope; not upstream pack temperature |
| sensor | 6831 | A | Battery pack 5 current | `a_6831` | Upstream equivalent |
| sensor | 6865 | electric heating state | Battery pack 5 electric heating state | `electric_heating_state_6865` | Modbus per-pack state; sensor domain retained |
| sensor | 7241 | system  Parallel mode | Device mode | `system_parallel_mode_7241` | Modbus description; scope retained |
| sensor | 7512 | PVtWh | Cumulative production | `pvt_wh_7512` | Upstream equivalent |
| sensor | 7519 | Day_B Charge Energy | Battery daily charging energy | `day_b_charge_energy_7519` | Upstream equivalent |
| sensor | 7521 | Day_B disCharge Energy | Battery daily discharging energy | `day_b_dis_charge_energy_7521` | Upstream equivalent |
| sensor | 7534 | Modbus Version | Modbus version | `modbus_version_7534` | Modbus description; scope retained |
| sensor | 7553 | Bypass  power | Bypass power | `bypass_power_7553` | Upstream equivalent |
| sensor | 7592 | Grid voltage | Grid frequency | `grid_voltage_7592` | Upstream equivalent |
| sensor | 7593 | Master Pack SOC | Main SOC | `master_pack_soc_7593` | Upstream equivalent |
| sensor | 7594 | Slave pack1 SOC | Battery pack 1 SOC | `slave_pack1_soc_7594` | Upstream equivalent |
| sensor | 7595 | Slave pack2 SOC | Battery pack 2 SOC | `slave_pack2_soc_7595` | Upstream equivalent |
| sensor | 7596 | Slave pack3 SOC | Battery pack 3 SOC | `slave_pack3_soc_7596` | Upstream equivalent |
| sensor | 7597 | Slave pack4 SOC | Battery pack 4 SOC | `slave_pack4_soc_7597` | Upstream equivalent |
| sensor | 7598 | Slave pack5 SOC | Battery pack 5 SOC | `slave_pack5_soc_7598` | Upstream equivalent |
| sensor | 7599 | Total SOC(Full-system SoC) | Battery SOC | `total_soc_full_system_so_c_7599` | Upstream equivalent |
| number | 1138 | ACchargeSpeed | Inverter input limit | `accharge_speed_1138` | Upstream equivalent |
| number | 1142 | BackUpSoc | Discharge limit | `back_up_soc_1142` | Upstream equivalent |
| number | 1146 | FeedBack Power | Feed-in power limit | `feed_back_power_1146` | Upstream equivalent |
| number | 1147 | AC max discharge power | Max AC output power | `ac_max_discharge_power_1147` | Upstream equivalent |
| number | 1151 | Realtime Control Power | Real-time control power | `realtime_control_power_1151` | Modbus description; scope retained |
| number | 1152 | Realtime Control end SOC | Real-time target SOC | `realtime_control_end_soc_1152` | Upstream equivalent |
| number | 1154 | OffGird BackUpSoc | Off-grid backup SOC | `off_gird_back_up_soc_1154` | Modbus description; scope retained |
| number | 7268 | Force Full Charge Interval | Forced full charge interval | `force_full_charge_interval_7268` | Modbus description; scope retained |
| select | 1144 | SystemMode | Energy mode | `system_mode_1144` | Upstream equivalent |
| select | 1150 | Realtime Control Order | Real-time command | `realtime_control_order_1150` | Modbus description; scope retained |
| select | 7265 | LED light strip enable | LED indicator | `led_light_strip_enable_7265` | Upstream equivalent |
| switch | 1143 | GridChargeEnable | Allow grid charging | `grid_charge_enable_1143` | Upstream equivalent |
| switch | 7266 | Bypass enable | Bypass socket | `bypass_enable_7266` | Upstream equivalent |

## Enum labels

| Address | Code | Original label | Display label |
| --- | --- | --- | --- |
| 1144 | 1 | Self-consumption | Self-consumption |
| 1144 | 4 | Realtime Control | Real-time control |
| 1144 | 6 | User-defined Time Control | Charge/discharge schedule |
| 1150 | 0 | DEFAULT | Default |
| 1150 | 1 | CHARGE | Charge |
| 1150 | 2 | DISCHAGE | Discharge |
| 7265 | 0 | Turn off LED strip | Off |
| 7265 | 1 | Turn on LED strip | On |
| 7265 | 2 | LED strip low power mode (half brightness) | Half brightness |
| 1246 | 0 | disconnect | Disconnected |
| 1246 | 1 | connect | Connected |
| 7241 | 0 | Normal Mode | Standalone |
| 7241 | 1 | Master Mode | Cluster (main) |
| 7241 | 2 | Slave Mode | Cluster (sub) |

Code 0 for real-time command remains “Default”: the protocol does not establish
that it means upstream “Standby”. Energy mode retains “Self-consumption” rather
than importing upstream's less clear “Self-consumed prioritized”. LED half
brightness remains a third option; it is not reduced to an HTTP switch.

## Deliberately unchanged or not equated

- AC energy counters 170, 196, 7510, 7545, 7549 and 7551: system scope,
  daily/cumulative scope or duplicate-counter relationships prevent copying
  upstream total AC/bypass energy labels.
- Signed AC power 174 and combined inverter/bypass power 1284: neither is
  relabeled as a separate system AC input/output measurement.
- `Evt1`, `DCEvt`, load points, `no fully charge time`, `CounterCurrentCharge`
  and other unmatched technical fields retain their names pending clearer
  evidence. No undocumented alarm meanings are inferred.
- Real-time control power 1151 keeps “control power”, because the description
  establishes a command value but does not establish HTTP power-limit semantics.
- Inverter voltage/frequency 110/116 are not grid measurements. Their names
  explicitly retain inverter scope; meter power 1247 retains phase U scope.
- The suspicious OFF/ON enum on daily microinverter energy 7547 is untouched;
  resolving that catalog issue is outside this presentation change.
