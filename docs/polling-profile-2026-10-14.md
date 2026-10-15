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

## Authorized 2-second spacing experiment — 0.2.1

Released commit `420ceef` as 0.2.1 after 56 integration tests, Ruff checks and
GitHub Tests/Lint/Validate passed. Changed the default spacing to 2s and explicitly
changed this device's saved spacing from 5s to 2s. Regular interval 30s and fast
battery target 5s were preserved. Saved overrides remain preserved on upgrade.
HACS installed 0.2.1; Home Assistant Core restart was initiated around
2026-10-14T09:44:40+02:00 (not an OS reboot). Live diagnostics confirmed 0.2.1,
protocol 24 and 30/5/2 settings after recovery. No battery mode or setpoint was
changed by this experiment. The built-in HTTP Indevolt entry remained disabled.
The second reported HTTP poller remains independently unverified.

### Initial trace after startup

Explicit retained trace window: 2026-10-14T09:48:46+02:00 through
2026-10-14T09:50:04+02:00, several minutes after restart.

- 32 completed reads, all successful in this trace.
- Nine battery completions: eight gaps, median 8.761s, mean 8.685s,
  range 7.373–10.034s. The 5s target is still not achieved.
- SOC reads completed at 09:48:46.996 and 09:49:46.999: 60.003s apart.
- Matched unit-1 TCP requests/responses: 32 pairs, median wire latency 0.410s,
  mean 0.451s, range 0.199–1.427s. Battery-only wire latency: nine pairs,
  median 0.352s, range 0.208–0.920s. Other Modbus units were excluded.
- Remote closes persisted. Examples: read completion 09:49:18.185, close
  09:49:18.203, reconnect 09:49:20.226; completion 09:49:42.185, close
  09:49:42.192, reconnect 09:49:44.195. These closes immediately after successful
  responses do not fit a simple five-second idle-timeout explanation. In these
  examples reconnects fit into normal 2s pacing instead of adding a 5s recovery.

### Resumed inspection later the same day

The work was interrupted and resumed on the user's request; this is not one
continuous debug capture. At 2026-10-14T13:37:52+02:00, diagnostics still showed
0.2.1, 30/5/2 settings, no current failed fields and 100 recent read durations.
Logging was explicitly restored to INFO and verified. Continuous DEBUG logging
coverage across the interruption was not established; the later retained logs
contain INFO reconnects rather than a complete per-read trace.

| Read operation duration, including pacing/recovery | Prior 5s spacing | 2s spacing, latest 100 |
| --- | ---: | ---: |
| Mean | 8.846s | 2.427s |
| Median | 10.289s | 2.357s |
| p95, nearest rank | 10.593s | 3.068s |
| Maximum | 13.309s | 3.632s |

Mean duration is approximately 72.6% lower (3.65 times the operation throughput
if continuously busy). These durations are not wire response latency.
Snapshot battery age was 6.382s, SOC age 32.245s, and maximum field age 57.685s,
compared with SOC age 322.430s in the earlier follow-up.

Recorder window: 2026-10-14T13:19:30+02:00 through
2026-10-14T13:37:50+02:00 (18m20s). Synthetic window-start states were excluded
from cadence calculations; no pagination remained.

- Battery: 119 numeric changes, 118 gaps, median 9.348s, mean 9.264s,
  p95 10.137s, range 7.281–18.646s; no unavailable state. Values ranged
  from -1837 to 2349 W. These are state-change gaps, not every successful poll.
- SOC: 19 numeric changes, 18 gaps, median 57.181s, mean 58.117s,
  range 55.855–65.183s; no unavailable state. SOC ranged 52.7–55.4%.
- The same time window contains 46 connection-established lines explicitly
  identifying the Indevolt endpoint, with median spacing 23.807s
  (range 22.738–25.247s). Remote-close lines precede these by mostly about 2s.
  Reconnection churn therefore persists despite better throughput.

### Interpretation and next steps

The shorter pacing substantially improves operation duration and battery/SOC
freshness in both available samples. Battery updates are now roughly 8–10s,
versus the prior short trace's 10.5–20.6s and the much earlier approximately
8-minute cadence. It is not yet a reliable 5s feedback source. The serial worker
and regular requests still delay fast reads; regular polling is also closer to
one minute than its configured 30s target under this workload.

This supports keeping the authorized 2s trial in place, but does not prove the
firmware's connection-close mechanism. The later battery workload is active,
unlike the earlier 0W/3.5% SOC baseline; restart, workload, time of day and the
unverified second HTTP poller are confounders. No current failures and no recorder
unavailability do not prove that no transient read failures occurred between
samples. Recommended next work: investigate the repeatable roughly ten-request
connection lifetime using a bounded transaction trace, then evaluate scheduler
priority/regular workload before pursuing tighter battery control-loop cadence.
Do not infer control-loop stability or write latency from these read measurements.

## Connection-lifetime and scheduler investigation — 13:42–13:43

Read-only investigation of runtime behavior; settings stayed 30/5/2. Temporarily
enabled DEBUG from INFO and restored INFO after fetching the trace. Retained
window: 2026-10-14T13:42:39+02:00 through 2026-10-14T13:43:38+02:00.
25 reads completed successfully, including seven battery reads. Battery completion
gaps were 9.314, 9.214, 10.497, 9.626, 9.509 and 9.543 seconds.

### Connection closures: strong ten-response pattern

Two fully captured connections each delivered transaction IDs 1 through 10,
then closed immediately after response 10:

| Connection established | Tenth response | Register | Remote-close log | Next connection |
| --- | --- | --- | --- | --- |
| 13:42:39.930 | 13:43:01.097 | 1150 | 13:43:01.109 | 13:43:03.122 |
| 13:43:03.122 | 13:43:25.949 | 7266 | 13:43:25.958 | 13:43:28.063 |

Closure followed response completion by 12ms and 9ms, on different registers.
The next requests succeeded; neither closure caused a failed read in this trace.
The response-to-next-send gaps were 2.028s and 2.117s, close to normal 2s pacing.
This is strong evidence for a device-side ten-request connection lifetime, not
proof of the firmware mechanism or a universal guarantee. A packet capture or
firmware documentation would be needed to establish TCP initiator/policy fully.
The tmodbus log label alone is not sufficient: its clean connection_lost callback
uses the same remote-close wording even for local teardown. However, the inspected
integration only closes on unload/shutdown/probe cleanup, and the inspected client
code has no ten-request close policy. No local teardown/retry warnings appeared
in the retained trace. Local dependency source versions may differ from HA's
installed transitive dependencies; the live transaction pattern is primary evidence.

Do not proactively disconnect after nine reads or replay writes to address this:
that would add churn without evidence of a benefit. Existing reconnect handling
is effective in this sample. Monitor disconnects separately from failed operations.

### Scheduler: deadline semantics and head-of-line blocking

In coordinator.py, _read sets group.due to completion + interval (line 172),
and _run considers a fast read only once this deadline has passed (line 189).
It then enters the transport's pacing gate. Thus the fast interval represents a
wait before starting a read operation, not a completion-to-completion target.
The worker also starts a regular read even when that operation will cross the
upcoming fast deadline. A regular read cannot be preempted once started.

Concrete timeline:

- Battery completes 13:42:40.290; next eligibility is 13:42:45.290.
- Regular reads complete 13:42:42.592 and 13:42:44.946.
- Since fast is not eligible yet, a third regular read starts and completes
  13:42:47.443, already 2.153s past the fast deadline.
- Battery request sends 13:42:49.444 after transport pacing and completes
  13:42:49.604. Total battery gap: 9.314s.

There is no closure during this gap. The scheduling policy, rather than reconnect
cost, explains it directly. The fairness rule requiring at least one regular read
between battery reads is not the immediate cause here: three regular reads run.

The observed ~2.43s average operation duration permits about 0.41 requests/s.
Even the enabled regular groups alone cannot all recur every 30s at that rate;
adding battery reads every 5s requires 0.20 requests/s by itself. Increasing fast
priority necessarily slows regular fields unless fewer requests are needed.
A rough budget with 18 regular groups leaves ~0.21 requests/s for regular work,
or about 85s per regular round before reserving capacity for writes/recovery.
This is a capacity estimate, not a measured guarantee.

### Recommended implementation

1. Give fast battery polling an explicit cadence target rather than a post-read
   delay: track the intended next sample deadline, account for expected pacing
   and read duration, and reserve the next request slot before it is missed.
   Skip missed slots instead of issuing catch-up bursts. Preserve write priority.
2. Before starting a regular read, check whether it would consume the next fast
   slot. Keep fairness and a bounded regular-work budget. Test slow reads, failures,
   writes/readbacks, cancellation and missed deadlines with a controlled clock.
3. Add diagnostics for selected-group counts, per-group successful-poll gaps,
   deadline lateness, queue wait, operation duration and disconnect counts. Keep
   wire latency separate from application timing and state-change history.
4. Budget regular telemetry realistically: approximately 90–120s for the present
   workload if pursuing ~5s battery cadence at 2s spacing, with SOC optionally on
   an intermediate schedule. Reducing selected requests is another option.
   Changing regular interval alone will not fix fast deadline semantics.

A ~5s battery cadence is plausible with two ~2.4s operations per cycle, but has
little headroom for writes or slow responses. This investigation does not validate
a closed-loop controller, write latency or guaranteed 5s updates. No scheduler
code, battery controls or polling settings were changed in this investigation.

## Deadline scheduler trial — 0.2.2, 14:04–14:09

Implemented and released commit `e6beee7` as 0.2.2. Fast polling now reserves a
completion deadline using an adaptive response estimate, holds regular work that
would consume that slot, skips missed/unreachable slots, and retains write
priority plus regular-read fairness. Diagnostics include per-group successful
poll gaps, completion lateness, success/failure counts, queued explicit-job waits
and disconnect counts since worker start. The settings default remains 30s for
regular polling; saved settings are preserved on upgrade.

Validation: 58 integration tests and Ruff lint/format passed locally; GitHub
Tests, Lint and Validate all passed. Controlled-clock tests exercise paced
five-second cadence with regular progress, skipped slots after a slow read,
failure backoff and connection-loss subscription cleanup. Existing tests cover
write priority, readback, no write replay and shutdown cancellation.

HACS installed 0.2.2 and Home Assistant Core was restarted around
2026-10-14T14:03:52+02:00. At 14:06:50, diagnostics confirmed loaded 0.2.2 and
**120s regular / 5s battery target / 2s spacing**. Only the regular polling option
was changed for this trial. No battery mode or setpoints were changed. No DEBUG
logging was needed; INFO was verified in the final diagnostic snapshot.

### Successful-poll measurements

Snapshot: 2026-10-14T14:09:29+02:00, after several minutes of polling. This is a
short startup/settling trial, not a long-term reliability test. There are 19
selected read groups: one battery group and 18 regular groups.

| Metric | Result |
| --- | ---: |
| Battery successful reads | 44 |
| Measured battery gaps | 43 |
| Battery gap median | 5.083s |
| Battery gap mean | 5.231s |
| Battery gap p95 (nearest rank) | 6.228s |
| Battery gap range | 2.509–6.975s |
| Fast completion lateness median / p95 / max | 0.381 / 2.435 / 3.740s |
| Successful reads, all groups | 79 |
| Failed operations, all groups | 1 |
| Disconnect notifications since worker start | 8 |
| Current failed fields | none |

These are successful-poll gaps measured by the coordinator, including unchanged
values. They improve substantially on the 0.2.1 trace's 9.2–10.5s gaps. The target
is approximate: a delayed sample may be followed by a shorter gap to the next
scheduled slot, subject to request pacing and regular-work fairness.

All regular groups were sampled. Seventeen groups have a second successful read,
with gaps between 120.263 and 124.830s. SOC's measured gap was 124.679s. The charge
speed field (1138) timed out once during startup and then succeeded on its next
scheduled retry. Its timeout remained visible for approximately the regular retry
interval; it has only one success and therefore no successful-poll gap yet.
Battery age at the snapshot was 1.993s and SOC age 19.806s. No explicit writes or
refresh jobs were observed in the queue metrics, so command latency remains
untested on hardware.

Recorder query: 2026-10-14T14:07:30+02:00 through
2026-10-14T14:09:29+02:00. Battery returned 24 state records and SOC two, with no
unavailable states or remaining pagination. These state records are not used as
the primary cadence measurement.

### Timing interpretation and limitations

The 80 read operations had mean 1.462s, median 1.336s, p95 2.966s and maximum
4.007s. This does **not** imply a faster wire response: the scheduler now spends
some idle time waiting for a reserved slot before entering the measured read
operation, so less pacing occurs inside that operation. Successful-poll cadence
is the appropriate before/after metric. No new wire trace was collected.

The eight disconnect notifications show that the scheduler change does not remove
connection churn. Their count is not a count of failed reads: only one failed
read was recorded. This supports retaining reconnect handling rather than adding
proactive connection cycling. Firmware-level close policy remains unproven.

The live result supports the combined scheduler and 120s workload-budget change.
Because both changed together, it does not isolate their individual contribution.
The controlled-clock test independently demonstrates the deadline behavior.
Regular telemetry, including SOC, is deliberately slower. A separate SOC cadence
can be considered later if a concrete control requirement needs it; no extra
SOC polling was introduced here. Five-second feedback is still best-effort, and
this short read-only trial does not establish closed-loop stability or behavior
under sustained writes. The authorized 120/5/2 settings remain active.

## One-second spacing / three-second battery trial — 18:46–18:49

User authorized the next timing experiment. On 2026-10-14 at approximately
18:45:58+02:00, changed saved options to **120s regular / 3s battery / 1s spacing**
through the official options flow, which reloads the integration. Version remains
0.2.2; no code release or HA restart was needed. Battery mode and setpoints were
not changed. Logging remained INFO and no control writes were tested.

The pre-change snapshot was taken around 18:07, before an interruption and the
user's request to continue. Its most recent 100 battery gaps had median 5.125s,
mean 5.013s, p95 7.008s and range 2.559–7.282s. Cumulative counters showed 2803
successful battery reads and 22 failed battery operations, with 37 failed reads
across all groups and 510 disconnect notifications over the longer prior run.
These cumulative counts cannot be directly compared with a three-minute trial.
The options change reset worker counters.

At approximately 18:49:18+02:00, the new worker reported:

| Metric | Result |
| --- | ---: |
| Successful battery reads | 66 |
| Battery successful-poll gaps | 65 |
| Gap median / mean | 3.014s / 2.999s |
| Gap p95 / maximum | 3.332s / 3.584s |
| Minimum gap | 2.611s |
| Completion lateness median / p95 / maximum | 0.012s / 0.304s / 0.539s |
| Successful reads across all groups | 102 |
| Failed reads across all groups | 0 |
| Disconnect notifications | 10 |
| Current failed fields | none |

All 18 regular groups completed two successful reads. Their 18 measured gaps
ranged from 120.173 to 120.598s (median 120.313s). Battery data age was 1.061s;
SOC age was 29.270s. No explicit-job queue waits or pending control workload were
observed. The last 100 operations averaged 0.555s, median 0.407s, p95 1.415s,
maximum 1.486s. These durations exclude scheduler waiting before each operation
and include any pacing/recovery inside it; they are not wire latency.

Recorder query used the explicit window 2026-10-14T18:46:10+02:00 through
2026-10-14T18:49:20+02:00. Battery had 56 state records and no unavailable state.
SOC's window-start record was unavailable while awaiting its initial read after
reload, then became available at 18:46:48.030 and updated at 18:48:48.321.
There was no subsequent SOC unavailability in this window. Neither history
query required pagination. Successful-poll counters, not state changes, supply
the cadence figures above.

Conclusion: the 120/3/1 trial achieved roughly three-second feedback, about 40%
shorter mean gaps than the latest five-second baseline, without failed reads in
this short sample. Disconnects persist and were recovered without failed reads.
Startup SOC availability and the much shorter observation window must be kept
separate from steady-state reliability. This does not validate sustained control
writes or long-term device tolerance. The authorized **120/3/1 settings remain
active**; no further timing reduction or ongoing monitor was configured.

## Next-morning follow-up — 15 October, 09:30

Read-only MCP inspection on 2026-10-15. History window:
**2026-10-15T09:12:00+02:00 through 2026-10-15T09:30:28+02:00** (18m28s).
Diagnostics and bounded logs were fetched around 09:30:35. Version remains 0.2.2,
HA 2026.10.1; settings remain **120s regular / 3s battery / 1s spacing**.
No settings, enablement, modes, setpoints or logging levels were changed. INFO
logging was sufficient; no new wire-latency capture was taken.

The built-in Indevolt HTTP integration remains user-disabled/not_loaded. Only
one HTTP Indevolt entry and one active Modbus entry match the integration search.
EVCC remains loaded; this does not establish whether its backend polls the battery.
The second reported HTTP poller is still unverified.

### Current cadence and freshness

| Measurement | Result |
| --- | ---: |
| Latest 100 successful battery-poll gaps: mean / median | 2.999 / 3.020s |
| Battery poll gaps: p95 / maximum / minimum | 3.689 / 4.053 / 1.585s |
| Latest 100 successful SOC-poll gaps: mean / median | 120.637 / 120.403s |
| SOC poll gaps: p95 / maximum | 121.779 / 123.688s |
| Battery / SOC data age at snapshot | 1.761 / 110.970s |
| Current failed fields | none |
| Last 100 operation durations: mean / median | 0.529 / 0.409s |
| Operation durations: p95 / maximum | 1.274 / 1.495s |

Successful-poll gaps include unchanged values. These rolling samples have
separate coverage: 100 battery gaps span about five minutes, whereas 100 SOC gaps
span several hours. Read-operation durations include pacing/recovery inside the
operation, exclude scheduler waiting before it, and are not wire latency.

Recorder returned 346 battery records, including the synthetic window-start
record; excluding that record leaves 345 numeric states and 344 gaps. State-change
gap median was 3.026s, mean 3.218s, p95 5.736s, range 1.585–8.959s. There were no
unavailable states. Power ranged from -790 to -532 W. Longer state-change gaps
can reflect unchanged readings and must not be labeled missed polls.

SOC returned ten records, including the synthetic initial record; nine numeric
changes yielded eight gaps, median 120.483s, range 120.196–121.813s. There were no
unavailable states. SOC ranged from 6.5% to 11.1%. Neither query had remaining
pagination.

### Failures and connection recovery

Current worker counters show 21,992 successful and 40 failed read operations
(0.182% failed), including 15,150 successful and 27 failed battery operations
(0.178% failed), and 2,207 disconnect notifications. These are cumulative worker
counters, not counts for the 18-minute history window or guaranteed counts since
yesterday's options change. A later bootstrap warning is present in system logs,
so worker lifetime must not be assumed continuous across yesterday and today.
No explicit-job queue waits were recorded; hardware control-write behavior remains
untested by this inspection.

Within the explicit history window, the retained INFO logs contain 53 connection
establishments identifying the Indevolt endpoint. Their 52 gaps have median
19.554s, mean 20.768s, range 16.212–30.109s. Reconnect count is not failed-read
count. At 09:23:43.741, tmodbus logged one unexpected transaction-ID-8 response
and discarded it. The warning lacks an endpoint identifier; the raw MBAP header
identifies unit 1, consistent with Indevolt, but endpoint attribution is not
conclusive without a paired request trace. This bounded log window does not prove
the absence of other errors. System-log search found a bootstrap warning rather
than a current Indevolt-specific error.

### Comparison and recommendation

The roughly three-second successful polling achieved in yesterday's short trial
is still present this morning: mean 2.999s versus 2.999s then; p95 is now 3.689s
versus 3.332s. The longer run reveals occasional failures that the initial short
trial did not capture. No recorded unavailability occurred in this morning's
18-minute window, compared with three episodes in the original 0.2.0 baseline.
Original battery state-change median was 19.171s, versus 3.026s now; SOC changes
were 279–333s apart, versus about 120s now. The much earlier approximately
eight-minute battery cadence has not returned in the measured sample.

This is not an isolated test of disabling HTTP pollers: integration version,
scheduler, regular interval, fast target, request spacing and workload all changed.
The second HTTP poller remains unverified. Do not attribute the improvement solely
to reduced HTTP traffic. Retain the current timing for now; the next useful
validation is bounded control-write responsiveness with agreed operating limits,
not further read-speed reduction. Connection-loss/late-response diagnosis remains
worthwhile, but does not currently prevent near-three-second telemetry. No new
monitor was scheduled by this follow-up.
