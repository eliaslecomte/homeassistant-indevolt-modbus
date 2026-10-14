# Indevolt Modbus polling profile — 14 October 2026

All times below use Europe/Brussels (UTC+02:00). Measurements were obtained
through Home Assistant MCP. No battery controls or polling settings were changed
during profiling; temporary DEBUG logging was restored to INFO.

## Baseline: HTTP pollers still enabled

History window: **00:20:00–00:38:28**. A subsequent short debug capture covered
approximately **00:39:07–00:40:03**.

| Configuration | Value |
| --- | --- |
| Installed integration | Indevolt Modbus 0.2.0 |
| Home Assistant | 2026.10.1 |
| Device protocol | V2.4 |
| Regular polling interval | 30 seconds |
| Fast battery power target | 5 seconds |
| Minimum request spacing | 5 seconds |

| Measurement | Result |
| --- | --- |
| Battery power state-change gaps between adjacent numeric states | Median 19.171s; minimum 10.844s; maximum 56.398s |
| Battery power unavailable episodes in history window | 3 |
| SOC state-change gaps, excluding the window's initial state | 279.414–333.300s; median 316.461s |
| Last 100 read-operation durations, including pacing/recovery | Mean 8.834s; median approximately 8.5s; p95 approximately 13.55s; maximum 14.905s |
| Successful battery read-completion gaps in short debug capture | Approximately 13–21s |
| Successful battery wire-response times in short capture | Approximately 0.32–1.20s |

Diagnostics showed timeout failures for discharge limit (1142) and bypass enable
(7266). Logs showed repeated remote TCP closures, a connection reset, and late
responses discarded as unexpected transaction IDs. Many regular fields had data
ages of several minutes. For comparison, before 0.2.0, battery state changes were
approximately eight minutes apart.

State-change gaps are **not** a count of every successful poll: unchanged values
need not produce recorder entries. Diagnostic operation durations include pacing
and connection recovery; they are **not** wire-response latency. The short capture
provides separate evidence of actual completed reads. Raw captures are not stored
here; these are summarized observations from this chat's MCP inspection.

The observed behavior is consistent with a saturated shared scheduler: fast and
regular reads alternate under load, and operations averaging roughly nine seconds
leave battery updates around eighteen seconds apart. Reconnection/recovery costs
are a likely contributor; the root cause of disconnections is not yet established.

## Intervention and planned comparison

At approximately **07:55–08:00**, the user reported having disabled **two HTTP
integrations that also polled this device**. Their identities and exact disable
times have not yet been verified. This is a potential reduction in concurrent
device traffic, not proof that HTTP polling caused the Modbus issues.

Repeat profiling around **09:30**, using a comparable recent 18-minute window.
Verify installed version, current polling settings and which integrations are
disabled before comparing. Measure battery/SOC state changes, unavailable episodes,
field ages, read-duration distributions, timeouts and reconnects. If needed, take
a bounded debug capture, then restore the previous log level. Do not alter modes,
power setpoints, polling settings or integration enablement for this comparison.

Record changes in settings, workload or device behavior as confounders. Append
the follow-up results here, including whether reduced HTTP traffic correlates with
improved latency and reliability. Do not infer causation from a single comparison.

## Follow-up after disabling HTTP pollers — 09:30

History window: **09:12:00–09:30:28** (18m 28s, matching the baseline).
Debug read completions sampled **09:31:05–09:32:14**. Installed integration 0.2.0,
HA 2026.10.1 and protocol V2.4 were unchanged. Options remained regular 30s,
fast battery 5s, request spacing 5s. No operating or polling settings were changed;
temporary debug logging was restored to INFO.

### Intervention verification

The built-in `indevolt` integration (INDEVOLT CMS-SF2000) was confirmed
`not_loaded`, disabled by the user. The registry contained only one Indevolt HTTP
entry and one active Indevolt Modbus entry. The second reported HTTP poller could
not be identified from the complete HA integration listing. `evcc_intg` remained
loaded, but that does not establish whether the EVCC backend still polls this
battery. The exact intervention and disable times therefore remain only partially
verified; no integrations were enabled or disabled during this check.

### Measurements

| Measurement | Earlier baseline | Follow-up |
| --- | --- | --- |
| Mean of last 100 read operations, including pacing/recovery | 8.834s | 8.846s |
| Median operation duration | Approximately 8.5s | 10.289s |
| p95 operation duration | Approximately 13.55s | 10.593s (nearest rank) |
| Maximum operation duration | 14.905s | 13.309s |
| Battery unavailable episodes in history window | 3 | 0 recorded |
| Diagnostic failed-register snapshot | 1142 and 7266 timeouts | Empty |
| Battery state-change cadence | Median 19.171s | Not measurable: constant 0 W |
| SOC state-change cadence | 279–333s | Not measurable: only one change, 3.6% to 3.5% |
| Battery read-completion gaps in bounded debug capture | Approximately 13–21s | 10.506, 10.653, 15.809 and 20.587s |
| Successful battery wire-response times in capture | Approximately 0.32–1.20s | 0.160–0.405s (5 reads) |

The 11 successful paired Modbus reads in the debug capture had wire-response times
of 0.160–0.487s. No failed reads appeared among those 11 coordinator completions.
The diagnostics snapshot still showed regular data ages up to **322.430s** (SOC);
battery power age was 14.359s. Unchanged recorder values must not be mistaken for
missing polls. The diagnostic rolling sample and short debug capture are separate
samples, not measurements of the entire history window.

### Connection behavior and interpretation

Repeated remote TCP closes and reconnects persisted. One illustrative sequence:

- Battery read completed at 09:31:48.277.
- Remote closed the connection at 09:31:53.293, about five seconds later.
- Reconnected at 09:31:58.316; the next read completed at 09:31:58.619.
- Remote closed again at 09:32:03.640; reconnection at 09:32:08.657 preceded a
  successful battery response at 09:32:08.862.

This is consistent with an approximately five-second idle timeout competing with
the configured five-second request spacing, followed by the recovery wrapper's
additional pacing wait. This is a strong diagnostic hypothesis, not a confirmed
firmware root cause. Current operations cluster near five or ten seconds even
though successful responses themselves take fractions of a second.

There is **no material improvement in mean operation time** after the reported
HTTP-poller reduction. Reliability indicators are better in these samples (no
recorded unavailable states, no current failed registers, smaller latency tail),
but the battery is now idle at 0 W and about 3.5% SOC, unlike the earlier active
battery. Combined with incomplete verification of the second poller and small
wire samples, this prevents attributing the differences solely to HTTP traffic.

Next investigation should focus on the connection-idle/pacing interaction. A
separately authorized trial with shorter request spacing could test that hypothesis
while holding other settings constant and measuring reconnect counts, completed
read cadence and error rates. Do not simply equate the 5s battery target with
achievable cadence: regular reads share the connection. No further follow-up was
scheduled by this one-time inspection.
