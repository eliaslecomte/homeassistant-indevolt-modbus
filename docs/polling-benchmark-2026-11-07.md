# Polling benchmark — 2026-11-07

Release: 0.2.9, code commit `58607cd`. Home Assistant 2026.11.0.
CMS-SF2000 installation with protocol V2.4, 25 enabled entities in 21 read groups.
All 344 registry entries, their unique IDs, entity IDs and enablement choices were
preserved. No battery control values were written during this verification.

## Automated verification

107 tests pass, with Ruff lint and formatting checks passing locally and on GitHub.
Tests cover per-tier classification and freshness, initial/manual reads, targeted
write readback, lifecycle, and an hour-long simulated workload using two-second
request pacing and simulated response time. Device clock words 1132–1134 use the
telemetry tier despite their catalog Settings classification.

## Live lifecycle checks

- 0.2.9 loaded after the user's Home Assistant restart.
- Turning off HA's automatic polling option reloaded the integration successfully.
  All read-group counters remained at zero during a 20-second observation.
- An explicit `homeassistant.update_entity` on ACOutW then read all 21 enabled
  groups exactly once, including settings and rated capacity, with zero failures.
  The service API response timed out after 30 seconds; diagnostics confirmed
  completion afterward, with no queued refresh reads. The request was not resent.
- Automatic polling was restored through the same system option, producing a
  fresh worker and fresh diagnostics counters for the benchmark below.
- All 25 enabled entities were available after the test. The values of all number,
  select and switch entities matched the earlier pre-test state snapshot.
- Marketplace warning acceptance was recorded for the MCP account after explicit
  user consent; the Marketplace reports 0.2.9 installed.

## Automatic-only sample

Window: **08:03:03–08:09:37 Europe/Brussels**, 6 minutes 34 seconds.
No explicit refreshes or control writes were issued during this window.
Counters cover the fresh worker's lifetime and may include a few seconds before
the recorded start, which was captured just after the system-option reload.
Measurements are successful read-completion gaps from diagnostics, not recorder
state-change gaps. Identical values need not create recorder updates.

| Tier | Target | Groups | Successful reads per group | Gap samples | Median | Mean | Range |
| --- | --- | ---: | --- | ---: | --- | --- | --- |
| ACOutW | 10 s | 1 | 40 | 39 | 9.985 s | 10.002 s | 8.591–11.320 s |
| Telemetry | 60 s | 10 | 6–7 | 54 | 62.153 s | 63.170 s | 60.265–72.446 s |
| Settings/modes | 300 s | 9 | 2 | 9 | 312.258 s | 310.614 s | 300.689–316.160 s |
| Rated capacity | 3600 s | 1 | 1 | 0 | Not observed | Not observed | Initial read only |

Telemetry and settings rows pool gaps across their read groups. Settings have only
one repeat per group, so this is not a long-term reliability measurement.

All **123 group reads succeeded**, the failed-field map was empty,
and no explicit reads or writes remained queued at the end. There were
**12 connection-loss notifications**; recovery continued to work without
failed group reads. The Modbus ERROR query against the system log returned no
entries. Recurring TCP disconnections remain a known behavior, not a resolved issue.

## Comparison with 0.2.8

The pre-update rolling diagnostics snapshot on the same enabled workload reported
ACOutW median 15.001 s and other-group pooled median
60.109 s. Those rolling samples span a different duration,
so they are context rather than a controlled, simultaneous comparison.
The new release delivers the intended faster ACOutW cadence and reduces settings
and information reads while preserving live telemetry near a minute.

## Limits and follow-up

- The hourly automatic repeat was verified by the simulated long-duration test.
  This live sample confirms the initial information read and that it did not
  repeat prematurely; it does not prove the live one-hour interval.
- Live targeted writes were not exercised because they would alter battery
  settings. Immediate targeted readback and write non-replay are covered by tests;
  live control entities were checked for availability and unchanged values.
- Cadences remain best-effort: the paced connection, retries, initial reads and
  coincident settings deadlines introduce jitter. ACOutW's measured average is
  approximately 10 seconds, not a guarantee that every gap is exactly 10 seconds.
- The two-second minimum request spacing is retained from 0.2.8. It is faster than
  the vendor's five-second recommendation, though above the one-second minimum.
- Protocol support is determined during setup; a firmware change that introduces
  registers still requires reloading the integration.

