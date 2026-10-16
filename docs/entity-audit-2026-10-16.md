# Entity audit — 2026-10-16

## Scope and initial observations

All 344 registered entities were enabled temporarily; original enablement was
23 enabled and 321 disabled. No control values, modes or polling options were
written. Runtime 0.2.4, device protocol 24 (V2.4); regular target 120 s,
ACOutW fast target 3 s, request spacing 1 s. All 147 read groups were attempted
between approximately 16:19 and 16:27 Europe/Brussels. Expanded polling means
samples below are not simultaneous, and regular targets cannot all be met.

342 registers read successfully: 339 usable entity states, three unknown enums.
Two other registers were rejected. A successful read is not necessarily a new
state or a physically accurate reading. Optional absent features can return zero.

## Confirmed fixes in 0.2.5

- Render documented decimal firmware and protocol versions, keeping raw numbers
  in `raw_value` attributes. Example EMS 10112 becomes V1.01.12.
- Render packed sleep, forced-charge and all 24 schedule start/end times as HH:MM.
  Schedule 1 end 5947 (0x173B) becomes 23:59. Split clock words are presented
  separately, not combined into a potentially inconsistent timestamp.
- Invalid packed times become unknown with the original value retained.
- Supply missing days (7268) and watts (7270), explicitly stated in vendor prose.
- Assign HA device classes for apparent power, reactive power and durations.
- Entity IDs, write bounds, signed power directions and wire decoding remain intact.

Source: [vendor register table](https://docs.indevolt.com/docs/hardware/open-data/modbus-register-table/),
checked 2026-10-16. Its unit columns for 7268/7270 are blank despite explicit units
in the descriptions. Versions/time formats are explicitly documented.

## Unresolved hardware/documentation discrepancies

- PV status registers 2247/2268/2288 each returned code **1**, confirmed by decoder
  warnings at 16:22:16–16:22:31. The vendor defines only 1003–1011. Keep unknown;
  mapping 1 to OFF or SLEEPING would be a guess. Requires vendor clarification.
- The shared read of microinverter counters 7545–7548 returned IllegalDataValueError.
  This does not identify which individual counter caused rejection. Unavailable
  is appropriate; protocol-version support alone does not guarantee every optional
  hardware feature. Do not invent zero energy or suppress exceptions.
- Main/pack-1 voltages were 6.70/6.65 V using the documented 0.01 multiplier.
  These look unusual for pack voltage; the definition currently agrees with our
  decoder. Do not change scale based only on plausibility. Compare with the
  vendor app/BMS measurement and obtain a model-specific definition.
- Pack currents (-34.5 A main, -9.4 A pack 1) and total battery power (-185 W)
  were read at different times. They cannot establish a power-balance or scale
  correction in this long polling pass.
- Remaining discharge time was 9999 min while charging. This may be a firmware
  sentinel, but the table defines no sentinel: retained as reported.
- Packs 2–5 report zero telemetry and firmware. This is consistent with absent
  packs, but zero alone does not prove absence; no inferred availability rules.
- Apparent/reactive power and power factor are zero while charging, which the
  vendor explicitly documents. The unusual `Pct` power-factor unit remains
  unchanged until nonzero readings clarify the vendor's scale convention.
- Enum states are numeric strings by design; HA uses translated UI labels.
  Bitfields remain numeric masks rather than pretending they are enums.

## Validation

Library: 40 tests plus Ruff and mypy. Integration: 90 tests plus Ruff, including
all 344 entities enabled together, HA state validation, formatting boundaries,
raw-value retention, unit metadata and existing signed-power regression tests.

Live post-install validation and restoration are recorded below after deployment.

## Initial complete inventory

Values reflect the last sample for each field at the end of the first pass.
Units below are the pre-release HA units; `—` means no unit, not missing data.

| Entity | Register | Initial state | Unit | Originally enabled |
|---|---:|---|---|---|
| `sensor.indevolt_ems_version` | 70 | 10112 | — | no |
| `sensor.indevolt_main_bms_version` | 71 | 10049 | — | no |
| `sensor.indevolt_inverter_version` | 72 | 141 | — | no |
| `sensor.indevolt_mppt_version` | 73 | 10177 | — | no |
| `sensor.indevolt_maximum_mppt_channels` | 78 | 4 | — | no |
| `sensor.indevolt_maximum_number_of_strings` | 80 | 6 | — | no |
| `sensor.indevolt_rated_output_power` | 81 | 2000 | W | no |
| `sensor.indevolt_maximum_active_power` | 83 | 1792 | W | no |
| `sensor.indevolt_rated_capacity` | 89 | 3584 | Wh | yes |
| `sensor.indevolt_maximum_charge_power` | 90 | 1792 | W | no |
| `sensor.indevolt_maximum_discharge_power` | 91 | 1792 | W | no |
| `sensor.indevolt_dcdc_slaver1_version` | 92 | 10177 | — | no |
| `sensor.indevolt_bms_slaver1_version` | 93 | 11049 | — | no |
| `sensor.indevolt_dcdc_slaver2_version` | 94 | 0 | — | no |
| `sensor.indevolt_bms_slaver2_version` | 95 | 0 | — | no |
| `sensor.indevolt_dcdc_slaver3_version` | 96 | 0 | — | no |
| `sensor.indevolt_bms_slaver3_version` | 97 | 0 | — | no |
| `sensor.indevolt_dcdc_slaver4_version` | 98 | 0 | — | no |
| `sensor.indevolt_bms_slaver4_version` | 99 | 0 | — | no |
| `sensor.indevolt_inverter_ac_current` | 103 | 1.2 | A | no |
| `sensor.indevolt_inverter_ac_voltage` | 110 | 232.0 | V | no |
| `sensor.indevolt_inverter_ac_frequency` | 116 | 50.0 | Hz | no |
| `sensor.indevolt_inverter_ac_apparent_output_power` | 118 | 0 | VA | no |
| `sensor.indevolt_ac_reactive_power` | 120 | 0 | var | no |
| `sensor.indevolt_inverter_ac_output_power_factor` | 122 | 0.0 | Pct | no |
| `sensor.indevolt_daily_production` | 124 | 0 | Wh | yes |
| `sensor.indevolt_system_operating_status` | 138 | 9 | — | no |
| `sensor.indevolt_evt1` | 140 | 0 | — | no |
| `sensor.indevolt_home_load_power` | 154 | 0 | — | no |
| `sensor.indevolt_ac_wh_input` | 170 | 1071449 | Wh | no |
| `sensor.indevolt_inv_input_power` | 174 | 502 | W | yes |
| `sensor.indevolt_day_ac_out_discharge_energy` | 198 | 0 | Wh | no |
| `sensor.indevolt_time_year_month` | 1132 | 6666 | — | no |
| `sensor.indevolt_time_day_hour` | 1133 | 4112 | — | no |
| `sensor.indevolt_time_min_sec` | 1134 | 4887 | — | no |
| `sensor.indevolt_standby_timeout` | 1140 | 120 | h | no |
| `sensor.indevolt_deep_sleep_start_time_hour_min` | 1155 | 0 | — | no |
| `sensor.indevolt_deep_sleep_stop_time_hour_min` | 1156 | 0 | — | no |
| `sensor.indevolt_meter_connection_state` | 1246 | 1 | — | no |
| `sensor.indevolt_meter_phase_u_power` | 1247 | -58 | W | no |
| `sensor.indevolt_battery_total_charging_energy` | 1269 | 969431 | Wh | yes |
| `sensor.indevolt_battery_total_discharging_energy` | 1271 | 915865 | Wh | yes |
| `sensor.indevolt_remaining_charging_time` | 1282 | 57 | min | no |
| `sensor.indevolt_remaining_discharging_time` | 1283 | 9999 | min | no |
| `sensor.indevolt_acoutw` | 1284 | 243 | W | yes |
| `sensor.indevolt_dc_input_current_1` | 2219 | 0.0 | A | no |
| `sensor.indevolt_dc_input_voltage_1` | 2220 | 2.5 | V | no |
| `sensor.indevolt_dc_input_power_1` | 2221 | 0 | W | no |
| `sensor.indevolt_dcevt` | 2228 | 0 | — | no |
| `sensor.indevolt_dc_input_current_2` | 2239 | 0.0 | A | no |
| `sensor.indevolt_dc_input_voltage_2` | 2240 | 2.5 | V | no |
| `sensor.indevolt_dc_input_power_2` | 2241 | 0 | W | no |
| `sensor.indevolt_dcst` | 2247 | unknown | — | no |
| `sensor.indevolt_dcevt_2` | 2248 | 0 | — | no |
| `sensor.indevolt_dc_output_power` | 2250 | 0 | W | yes |
| `sensor.indevolt_dc_input_current_3` | 2260 | 0.0 | A | no |
| `sensor.indevolt_dc_input_voltage_3` | 2261 | 2.5 | V | no |
| `sensor.indevolt_dc_input_power_3` | 2262 | 0 | W | no |
| `sensor.indevolt_dcst_2` | 2268 | unknown | — | no |
| `sensor.indevolt_dcevt_3` | 2269 | 0 | — | no |
| `sensor.indevolt_dc_input_current_4` | 2280 | 0.0 | A | no |
| `sensor.indevolt_dc_input_voltage_4` | 2281 | 2.5 | V | no |
| `sensor.indevolt_dc_input_power_4` | 2282 | 0 | W | no |
| `sensor.indevolt_dcst_3` | 2288 | unknown | — | no |
| `sensor.indevolt_dcevt_4` | 2289 | 0 | — | no |
| `sensor.indevolt_soh` | 6007 | 100 | % | no |
| `sensor.indevolt_main_cycles` | 6008 | 263 | — | no |
| `sensor.indevolt_main_voltage` | 6010 | 6.7 | V | no |
| `sensor.indevolt_main_battery_minimum_cell_temperature` | 6018 | 37 | °C | no |
| `sensor.indevolt_main_current` | 6108 | -34.5 | A | no |
| `sensor.indevolt_soh_2` | 6119 | 100 | % | no |
| `sensor.indevolt_battery_pack_1_cycles` | 6120 | 256 | — | no |
| `sensor.indevolt_battery_pack_1_voltage` | 6122 | 6.65 | V | no |
| `sensor.indevolt_battery_pack_1_minimum_cell_temperature` | 6130 | 34 | °C | no |
| `sensor.indevolt_battery_pack_1_current` | 6220 | -9.4 | A | no |
| `sensor.indevolt_soh_3` | 6231 | 0 | % | no |
| `sensor.indevolt_battery_pack_2_cycles` | 6232 | 0 | — | no |
| `sensor.indevolt_battery_pack_2_voltage` | 6234 | 0.0 | V | no |
| `sensor.indevolt_battery_pack_2_minimum_cell_temperature` | 6242 | 0 | °C | no |
| `sensor.indevolt_battery_pack_2_current` | 6332 | 0.0 | A | no |
| `sensor.indevolt_soh_4` | 6343 | 0 | % | no |
| `sensor.indevolt_battery_pack_3_cycles` | 6344 | 0 | — | no |
| `sensor.indevolt_battery_pack_3_voltage` | 6346 | 0.0 | V | no |
| `sensor.indevolt_battery_pack_3_minimum_cell_temperature` | 6354 | 0 | °C | no |
| `sensor.indevolt_battery_pack_3_current` | 6444 | 0.0 | A | no |
| `sensor.indevolt_soh_5` | 6455 | 0 | % | no |
| `sensor.indevolt_battery_pack_4_cycles` | 6456 | 0 | — | no |
| `sensor.indevolt_battery_pack_4_voltage` | 6458 | 0.0 | V | no |
| `sensor.indevolt_battery_pack_4_minimum_cell_temperature` | 6466 | 0 | °C | no |
| `sensor.indevolt_battery_pack_4_current` | 6556 | 0.0 | A | no |
| `sensor.indevolt_battery_charge_discharge_state` | 6563 | 1 | — | yes |
| `sensor.indevolt_battery_power` | 6564 | -185 | W | yes |
| `sensor.indevolt_dc_dc_state` | 6588 | 1 | — | no |
| `sensor.indevolt_main_electric_heating_state` | 6593 | 0 | — | no |
| `sensor.indevolt_electric_heating_temperature` | 6594 | 37 | °C | no |
| `sensor.indevolt_electric_heating_power` | 6595 | 0 | W | no |
| `sensor.indevolt_dc_dc_state_2` | 6620 | 1 | — | no |
| `sensor.indevolt_battery_pack_1_electric_heating_state` | 6625 | 0 | — | no |
| `sensor.indevolt_electric_heating_temperature_2` | 6626 | 33 | °C | no |
| `sensor.indevolt_electric_heating_power_2` | 6627 | 0 | W | no |
| `sensor.indevolt_dc_dc_state_3` | 6652 | 0 | — | no |
| `sensor.indevolt_battery_pack_2_electric_heating_state` | 6657 | 0 | — | no |
| `sensor.indevolt_electric_heating_temperature_3` | 6658 | 0 | °C | no |
| `sensor.indevolt_electric_heating_power_3` | 6659 | 0 | W | no |
| `sensor.indevolt_dc_dc_state_4` | 6684 | 0 | — | no |
| `sensor.indevolt_battery_pack_3_electric_heating_state` | 6689 | 0 | — | no |
| `sensor.indevolt_electric_heating_temperature_4` | 6690 | 0 | °C | no |
| `sensor.indevolt_electric_heating_power_4` | 6691 | 0 | W | no |
| `sensor.indevolt_dc_dc_state_5` | 6716 | 0 | — | no |
| `sensor.indevolt_battery_pack_4_electric_heating_state` | 6721 | 0 | — | no |
| `sensor.indevolt_electric_heating_temperature_5` | 6722 | 0 | °C | no |
| `sensor.indevolt_electric_heating_power_5` | 6723 | 0 | W | no |
| `sensor.indevolt_soh_6` | 6730 | 0 | % | no |
| `sensor.indevolt_battery_pack_5_cycles` | 6731 | 0 | — | no |
| `sensor.indevolt_battery_pack_5_voltage` | 6733 | 0.0 | V | no |
| `sensor.indevolt_battery_pack_5_minimum_cell_temperature` | 6741 | 0 | °C | no |
| `sensor.indevolt_battery_pack_5_current` | 6831 | 0.0 | A | no |
| `sensor.indevolt_dc_dc_state_6` | 6860 | 0 | — | no |
| `sensor.indevolt_battery_pack_5_electric_heating_state` | 6865 | 0 | — | no |
| `sensor.indevolt_electric_heating_temperature_6` | 6866 | 0 | °C | no |
| `sensor.indevolt_electric_heating_power_6` | 6867 | 0 | W | no |
| `sensor.indevolt_platform_connection_state` | 7075 | 0 | — | no |
| `sensor.indevolt_load_point_1` | 7080 | 800 | W | no |
| `sensor.indevolt_load_point_2` | 7081 | 800 | W | no |
| `sensor.indevolt_load_point_3` | 7082 | 800 | W | no |
| `sensor.indevolt_load_point_4` | 7083 | 800 | W | no |
| `sensor.indevolt_load_point_5` | 7084 | 800 | W | no |
| `sensor.indevolt_load_point_6` | 7085 | 800 | W | no |
| `sensor.indevolt_load_point_7` | 7086 | 800 | W | no |
| `sensor.indevolt_load_point_8` | 7087 | 800 | W | no |
| `sensor.indevolt_load_point_9` | 7088 | 800 | W | no |
| `sensor.indevolt_load_point_10` | 7089 | 800 | W | no |
| `sensor.indevolt_load_point_11` | 7090 | 800 | W | no |
| `sensor.indevolt_load_point_12` | 7091 | 800 | W | no |
| `sensor.indevolt_load_point_13` | 7092 | 800 | W | no |
| `sensor.indevolt_load_point_14` | 7093 | 800 | W | no |
| `sensor.indevolt_load_point_15` | 7094 | 800 | W | no |
| `sensor.indevolt_load_point_16` | 7095 | 800 | W | no |
| `sensor.indevolt_load_point_17` | 7096 | 800 | W | no |
| `sensor.indevolt_load_point_18` | 7097 | 800 | W | no |
| `sensor.indevolt_load_point_19` | 7098 | 800 | W | no |
| `sensor.indevolt_load_point_20` | 7099 | 800 | W | no |
| `sensor.indevolt_load_point_21` | 7100 | 800 | W | no |
| `sensor.indevolt_load_point_22` | 7101 | 800 | W | no |
| `sensor.indevolt_load_point_23` | 7102 | 800 | W | no |
| `sensor.indevolt_load_point_24` | 7103 | 800 | W | no |
| `sensor.indevolt_load_point_25` | 7104 | 800 | W | no |
| `sensor.indevolt_load_point_26` | 7105 | 800 | W | no |
| `sensor.indevolt_load_point_27` | 7106 | 800 | W | no |
| `sensor.indevolt_load_point_28` | 7107 | 800 | W | no |
| `sensor.indevolt_load_point_29` | 7108 | 800 | W | no |
| `sensor.indevolt_load_point_30` | 7109 | 800 | W | no |
| `sensor.indevolt_load_point_31` | 7110 | 800 | W | no |
| `sensor.indevolt_load_point_32` | 7111 | 800 | W | no |
| `sensor.indevolt_load_point_33` | 7112 | 800 | W | no |
| `sensor.indevolt_load_point_34` | 7113 | 800 | W | no |
| `sensor.indevolt_load_point_35` | 7114 | 800 | W | no |
| `sensor.indevolt_load_point_36` | 7115 | 800 | W | no |
| `sensor.indevolt_load_point_37` | 7116 | 800 | W | no |
| `sensor.indevolt_load_point_38` | 7117 | 800 | W | no |
| `sensor.indevolt_load_point_39` | 7118 | 800 | W | no |
| `sensor.indevolt_load_point_40` | 7119 | 800 | W | no |
| `sensor.indevolt_load_point_41` | 7120 | 800 | W | no |
| `sensor.indevolt_load_point_42` | 7121 | 800 | W | no |
| `sensor.indevolt_load_point_43` | 7122 | 800 | W | no |
| `sensor.indevolt_load_point_44` | 7123 | 800 | W | no |
| `sensor.indevolt_load_point_45` | 7124 | 800 | W | no |
| `sensor.indevolt_load_point_46` | 7125 | 800 | W | no |
| `sensor.indevolt_load_point_47` | 7126 | 800 | W | no |
| `sensor.indevolt_load_point_48` | 7127 | 800 | W | no |
| `sensor.indevolt_smartsocketstate` | 7238 | 0 | — | no |
| `sensor.indevolt_smartsocketp` | 7239 | 0 | W | no |
| `sensor.indevolt_grid_standard_code` | 7240 | 19 | — | no |
| `sensor.indevolt_device_mode` | 7241 | 0 | — | no |
| `sensor.indevolt_system_parallel_type` | 7242 | 0 | — | no |
| `sensor.indevolt_force_full_charge_start_time` | 7269 | 0 | — | no |
| `sensor.indevolt_full_charge_calibration` | 7271 | 0 | — | no |
| `sensor.indevolt_user_defined_period_1_start_time` | 7300 | 0 | — | no |
| `sensor.indevolt_user_defined_period_1_end_time` | 7301 | 5947 | — | no |
| `sensor.indevolt_user_defined_period_1_act` | 7302 | 0 | — | no |
| `sensor.indevolt_user_defined_period_1_act_w` | 7303 | 0 | W | no |
| `sensor.indevolt_user_defined_period_1_end_soc` | 7304 | 50 | % | no |
| `sensor.indevolt_user_defined_period_2_start_time` | 7305 | 0 | — | no |
| `sensor.indevolt_user_defined_period_2_end_time` | 7306 | 0 | — | no |
| `sensor.indevolt_user_defined_period_2_act` | 7307 | 0 | — | no |
| `sensor.indevolt_user_defined_period_2_act_w` | 7308 | 0 | W | no |
| `sensor.indevolt_user_defined_period_2_end_soc` | 7309 | 5 | % | no |
| `sensor.indevolt_user_defined_period_3_start_time` | 7310 | 0 | — | no |
| `sensor.indevolt_user_defined_period_3_end_time` | 7311 | 0 | — | no |
| `sensor.indevolt_user_defined_period_3_act` | 7312 | 0 | — | no |
| `sensor.indevolt_user_defined_period_3_act_w` | 7313 | 0 | W | no |
| `sensor.indevolt_user_defined_period_3_end_soc` | 7314 | 5 | % | no |
| `sensor.indevolt_user_defined_period_4_start_time` | 7315 | 0 | — | no |
| `sensor.indevolt_user_defined_period_4_end_time` | 7316 | 0 | — | no |
| `sensor.indevolt_user_defined_period_4_act` | 7317 | 0 | — | no |
| `sensor.indevolt_user_defined_period_4_act_w` | 7318 | 0 | W | no |
| `sensor.indevolt_user_defined_period_4_end_soc` | 7319 | 5 | % | no |
| `sensor.indevolt_user_defined_period_5_start_time` | 7320 | 0 | — | no |
| `sensor.indevolt_user_defined_period_5_end_time` | 7321 | 0 | — | no |
| `sensor.indevolt_user_defined_period_5_act` | 7322 | 0 | — | no |
| `sensor.indevolt_user_defined_period_5_act_w` | 7323 | 0 | W | no |
| `sensor.indevolt_user_defined_period_5_end_soc` | 7324 | 5 | % | no |
| `sensor.indevolt_user_defined_period_6_start_time` | 7325 | 0 | — | no |
| `sensor.indevolt_user_defined_period_6_end_time` | 7326 | 0 | — | no |
| `sensor.indevolt_user_defined_period_6_act` | 7327 | 0 | — | no |
| `sensor.indevolt_user_defined_period_6_act_w` | 7328 | 0 | W | no |
| `sensor.indevolt_user_defined_period_6_end_soc` | 7329 | 5 | % | no |
| `sensor.indevolt_user_defined_period_7_start_time` | 7330 | 0 | — | no |
| `sensor.indevolt_user_defined_period_7_end_time` | 7331 | 0 | — | no |
| `sensor.indevolt_user_defined_period_7_act` | 7332 | 0 | — | no |
| `sensor.indevolt_user_defined_period_7_act_w` | 7333 | 0 | W | no |
| `sensor.indevolt_user_defined_period_7_end_soc` | 7334 | 5 | % | no |
| `sensor.indevolt_user_defined_period_8_start_time` | 7335 | 0 | — | no |
| `sensor.indevolt_user_defined_period_8_end_time` | 7336 | 0 | — | no |
| `sensor.indevolt_user_defined_period_8_act` | 7337 | 0 | — | no |
| `sensor.indevolt_user_defined_period_8_act_w` | 7338 | 0 | W | no |
| `sensor.indevolt_user_defined_period_8_end_soc` | 7339 | 5 | % | no |
| `sensor.indevolt_user_defined_period_9_start_time` | 7340 | 0 | — | no |
| `sensor.indevolt_user_defined_period_9_end_time` | 7341 | 0 | — | no |
| `sensor.indevolt_user_defined_period_9_act` | 7342 | 0 | — | no |
| `sensor.indevolt_user_defined_period_9_act_w` | 7343 | 0 | W | no |
| `sensor.indevolt_user_defined_period_9_end_soc` | 7344 | 5 | % | no |
| `sensor.indevolt_user_defined_period_10_start_time` | 7345 | 0 | — | no |
| `sensor.indevolt_user_defined_period_10_end_time` | 7346 | 0 | — | no |
| `sensor.indevolt_user_defined_period_10_act` | 7347 | 0 | — | no |
| `sensor.indevolt_user_defined_period_10_act_w` | 7348 | 0 | W | no |
| `sensor.indevolt_user_defined_period_10_end_soc` | 7349 | 5 | % | no |
| `sensor.indevolt_user_defined_period_11_start_time` | 7350 | 0 | — | no |
| `sensor.indevolt_user_defined_period_11_end_time` | 7351 | 0 | — | no |
| `sensor.indevolt_user_defined_period_11_act` | 7352 | 0 | — | no |
| `sensor.indevolt_user_defined_period_11_act_w` | 7353 | 0 | W | no |
| `sensor.indevolt_user_defined_period_11_end_soc` | 7354 | 5 | % | no |
| `sensor.indevolt_user_defined_period_12_start_time` | 7355 | 0 | — | no |
| `sensor.indevolt_user_defined_period_12_end_time` | 7356 | 0 | — | no |
| `sensor.indevolt_user_defined_period_12_act` | 7357 | 0 | — | no |
| `sensor.indevolt_user_defined_period_12_act_w` | 7358 | 0 | W | no |
| `sensor.indevolt_user_defined_period_12_end_soc` | 7359 | 5 | % | no |
| `sensor.indevolt_user_defined_period_13_start_time` | 7360 | 0 | — | no |
| `sensor.indevolt_user_defined_period_13_end_time` | 7361 | 0 | — | no |
| `sensor.indevolt_user_defined_period_13_act` | 7362 | 0 | — | no |
| `sensor.indevolt_user_defined_period_13_act_w` | 7363 | 0 | W | no |
| `sensor.indevolt_user_defined_period_13_end_soc` | 7364 | 5 | % | no |
| `sensor.indevolt_user_defined_period_14_start_time` | 7365 | 0 | — | no |
| `sensor.indevolt_user_defined_period_14_end_time` | 7366 | 0 | — | no |
| `sensor.indevolt_user_defined_period_14_act` | 7367 | 0 | — | no |
| `sensor.indevolt_user_defined_period_14_act_w` | 7368 | 0 | W | no |
| `sensor.indevolt_user_defined_period_14_end_soc` | 7369 | 5 | % | no |
| `sensor.indevolt_user_defined_period_15_start_time` | 7370 | 0 | — | no |
| `sensor.indevolt_user_defined_period_15_end_time` | 7371 | 0 | — | no |
| `sensor.indevolt_user_defined_period_15_act` | 7372 | 0 | — | no |
| `sensor.indevolt_user_defined_period_15_act_w` | 7373 | 0 | W | no |
| `sensor.indevolt_user_defined_period_15_end_soc` | 7374 | 5 | % | no |
| `sensor.indevolt_user_defined_period_16_start_time` | 7375 | 0 | — | no |
| `sensor.indevolt_user_defined_period_16_end_time` | 7376 | 0 | — | no |
| `sensor.indevolt_user_defined_period_16_act` | 7377 | 0 | — | no |
| `sensor.indevolt_user_defined_period_16_act_w` | 7378 | 0 | W | no |
| `sensor.indevolt_user_defined_period_16_end_soc` | 7379 | 5 | % | no |
| `sensor.indevolt_user_defined_period_17_start_time` | 7380 | 0 | — | no |
| `sensor.indevolt_user_defined_period_17_end_time` | 7381 | 0 | — | no |
| `sensor.indevolt_user_defined_period_17_act` | 7382 | 0 | — | no |
| `sensor.indevolt_user_defined_period_17_act_w` | 7383 | 0 | W | no |
| `sensor.indevolt_user_defined_period_17_end_soc` | 7384 | 5 | % | no |
| `sensor.indevolt_user_defined_period_18_start_time` | 7385 | 0 | — | no |
| `sensor.indevolt_user_defined_period_18_end_time` | 7386 | 0 | — | no |
| `sensor.indevolt_user_defined_period_18_act` | 7387 | 0 | — | no |
| `sensor.indevolt_user_defined_period_18_act_w` | 7388 | 0 | W | no |
| `sensor.indevolt_user_defined_period_18_end_soc` | 7389 | 5 | % | no |
| `sensor.indevolt_user_defined_period_19_start_time` | 7390 | 0 | — | no |
| `sensor.indevolt_user_defined_period_19_end_time` | 7391 | 0 | — | no |
| `sensor.indevolt_user_defined_period_19_act` | 7392 | 0 | — | no |
| `sensor.indevolt_user_defined_period_19_act_w` | 7393 | 0 | W | no |
| `sensor.indevolt_user_defined_period_19_end_soc` | 7394 | 5 | % | no |
| `sensor.indevolt_user_defined_period_20_start_time` | 7395 | 0 | — | no |
| `sensor.indevolt_user_defined_period_20_end_time` | 7396 | 0 | — | no |
| `sensor.indevolt_user_defined_period_20_act` | 7397 | 0 | — | no |
| `sensor.indevolt_user_defined_period_20_act_w` | 7398 | 0 | W | no |
| `sensor.indevolt_user_defined_period_20_end_soc` | 7399 | 5 | % | no |
| `sensor.indevolt_user_defined_period_21_start_time` | 7400 | 0 | — | no |
| `sensor.indevolt_user_defined_period_21_end_time` | 7401 | 0 | — | no |
| `sensor.indevolt_user_defined_period_21_act` | 7402 | 0 | — | no |
| `sensor.indevolt_user_defined_period_21_act_w` | 7403 | 0 | W | no |
| `sensor.indevolt_user_defined_period_21_end_soc` | 7404 | 5 | % | no |
| `sensor.indevolt_user_defined_period_22_start_time` | 7405 | 0 | — | no |
| `sensor.indevolt_user_defined_period_22_end_time` | 7406 | 0 | — | no |
| `sensor.indevolt_user_defined_period_22_act` | 7407 | 0 | — | no |
| `sensor.indevolt_user_defined_period_22_act_w` | 7408 | 0 | W | no |
| `sensor.indevolt_user_defined_period_22_end_soc` | 7409 | 5 | % | no |
| `sensor.indevolt_user_defined_period_23_start_time` | 7410 | 0 | — | no |
| `sensor.indevolt_user_defined_period_23_end_time` | 7411 | 0 | — | no |
| `sensor.indevolt_user_defined_period_23_act` | 7412 | 0 | — | no |
| `sensor.indevolt_user_defined_period_23_act_w` | 7413 | 0 | W | no |
| `sensor.indevolt_user_defined_period_23_end_soc` | 7414 | 5 | % | no |
| `sensor.indevolt_user_defined_period_24_start_time` | 7415 | 0 | — | no |
| `sensor.indevolt_user_defined_period_24_end_time` | 7416 | 0 | — | no |
| `sensor.indevolt_user_defined_period_24_act` | 7417 | 0 | — | no |
| `sensor.indevolt_user_defined_period_24_act_w` | 7418 | 0 | W | no |
| `sensor.indevolt_user_defined_period_24_end_soc` | 7419 | 5 | % | no |
| `sensor.indevolt_actinwh` | 7510 | 1071450 | Wh | no |
| `sensor.indevolt_cumulative_production` | 7512 | 0 | Wh | yes |
| `sensor.indevolt_battery_daily_charging_energy` | 7519 | 4298 | Wh | yes |
| `sensor.indevolt_battery_daily_discharging_energy` | 7521 | 1147 | Wh | yes |
| `sensor.indevolt_modbus_version` | 7534 | 24 | — | no |
| `sensor.indevolt_off_grid_rated_voltage` | 7537 | 230 | V | no |
| `sensor.indevolt_off_grid_rated_frequency` | 7538 | 50 | Hz | no |
| `sensor.indevolt_off_grid_rated_power` | 7539 | 2400 | W | no |
| `sensor.indevolt_mppt_rated_power` | 7540 | 2400 | W | no |
| `sensor.indevolt_on_grid_rated_power` | 7541 | 2000 | W | no |
| `sensor.indevolt_microinverter_generation_energy` | 7545 | unavailable | Wh | no |
| `sensor.indevolt_day_microinverter_generation_energy` | 7547 | unavailable | — | no |
| `sensor.indevolt_day_on_grid_output_energy` | 7549 | 937 | Wh | no |
| `sensor.indevolt_day_off_grid_output_energy` | 7551 | 0 | Wh | no |
| `sensor.indevolt_bypass_power` | 7553 | 0 | W | yes |
| `sensor.indevolt_bypass_mode` | 7554 | 0 | — | no |
| `sensor.indevolt_cms_module_reset_req` | 7560 | 0 | — | no |
| `sensor.indevolt_system_shutdown_count` | 7586 | 30 | — | no |
| `sensor.indevolt_grid_voltage` | 7591 | 233.1 | V | no |
| `sensor.indevolt_grid_frequency` | 7592 | 50.0 | Hz | no |
| `sensor.indevolt_main_soc` | 7593 | 88.1 | % | no |
| `sensor.indevolt_battery_pack_1_soc` | 7594 | 88.5 | % | no |
| `sensor.indevolt_battery_pack_2_soc` | 7595 | 0.0 | % | no |
| `sensor.indevolt_battery_pack_3_soc` | 7596 | 0.0 | % | no |
| `sensor.indevolt_battery_pack_4_soc` | 7597 | 0.0 | % | no |
| `sensor.indevolt_battery_pack_5_soc` | 7598 | 0.0 | % | no |
| `sensor.indevolt_battery_soc` | 7599 | 87.9 | % | yes |
| `sensor.indevolt_no_fully_charge_time` | 7600 | 2874 | h | no |
| `sensor.indevolt_dcdc_slave5_version` | 10000 | 0 | — | no |
| `sensor.indevolt_bms_slave5_version` | 10001 | 0 | — | no |
| `number.indevolt_inverter_input_limit` | 1138 | 2000 | W | yes |
| `number.indevolt_discharge_limit` | 1142 | 5 | % | yes |
| `number.indevolt_feed_in_power_limit` | 1146 | 2000 | W | yes |
| `number.indevolt_max_ac_output_power` | 1147 | 2000 | W | yes |
| `number.indevolt_real_time_control_power` | 1151 | 101 | W | no |
| `number.indevolt_real_time_target_soc` | 1152 | 5 | % | no |
| `number.indevolt_off_grid_backup_soc` | 1154 | 10 | % | no |
| `number.indevolt_forced_full_charge_interval` | 7268 | 0 | — | no |
| `number.indevolt_forced_ac_charge_power` | 7270 | 500 | — | no |
| `select.indevolt_energy_mode` | 1144 | 1 | — | yes |
| `select.indevolt_real_time_command` | 1150 | 2 | — | yes |
| `select.indevolt_led_indicator` | 7265 | 1 | — | yes |
| `switch.indevolt_allow_grid_charging` | 1143 | on | — | yes |
| `switch.indevolt_bypass_socket` | 7266 | off | — | yes |
| `switch.indevolt_key_load_enable` | 7267 | off | — | no |
| `switch.indevolt_countercurrentcharge` | 7272 | on | — | no |
| `sensor.indevolt_ac_out_discharge_energy` | 196 | 0 | Wh | no |
