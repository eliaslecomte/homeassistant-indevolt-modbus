"""Schedule selected register reads and control writes on one device worker."""

import asyncio
import logging
from collections import deque
from dataclasses import dataclass, field
from time import monotonic
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from modbus_connection import ModbusError
from modbus_connection.model import UpdateReport

from .const import (
    CONF_FAST_POLL_INTERVAL,
    CONF_MESSAGE_SPACING,
    DOMAIN,
    MESSAGE_SPACING,
    SCAN_INTERVAL,
)
from .vendor.indevolt_modbus import IndevoltComponent, IndevoltDevice, Register

_LOGGER = logging.getLogger(__name__)
type IndevoltConfigEntry = ConfigEntry[IndevoltCoordinator]


@dataclass
class ReadGroup:
    """A single contiguous request and its completion-based deadline."""

    reader: IndevoltComponent
    interval: float
    fast: bool = False
    due: float = 0
    failures: int = 0
    successes: int = 0
    errors: int = 0
    last_success: float | None = None
    gaps: deque[float] = field(default_factory=lambda: deque(maxlen=100))
    lateness: deque[float] = field(default_factory=lambda: deque(maxlen=100))


@dataclass
class Job:
    """An explicit read or write requested by an entity or refresh."""

    group: ReadGroup
    done: asyncio.Future[None]
    register: Register | None = None
    value: float = 0
    queued_at: float = field(default_factory=lambda: monotonic())


class IndevoltCoordinator(DataUpdateCoordinator[UpdateReport]):
    """Publish each read immediately; serialize reads, writes and readbacks."""

    def __init__(
        self, hass: HomeAssistant, entry: IndevoltConfigEntry, device: IndevoltDevice
    ) -> None:
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN)
        self.device = device
        self.regular_interval = entry.options.get(CONF_SCAN_INTERVAL, SCAN_INTERVAL)
        self.fast_interval = entry.options.get(CONF_FAST_POLL_INTERVAL, 0)
        self.message_spacing = entry.options.get(CONF_MESSAGE_SPACING, MESSAGE_SPACING)
        self.values: dict[str, Any] = {}
        self.last_success: dict[str, float] = {}
        self.read_durations: deque[float] = deque(maxlen=100)
        self._report = UpdateReport()
        self._groups: list[ReadGroup] = []
        self._contexts: set[str] = set()
        self._writes: deque[Job] = deque()
        self._reads: deque[Job] = deque()
        self._wake = asyncio.Event()
        self._worker: asyncio.Task[None] | None = None
        self._last_fast = False
        self._last_operation_finished: float | None = None
        self._response_estimate = 0.4
        self.disconnect_count = 0
        self.job_queue_waits: deque[float] = deque(maxlen=100)
        self._unsubscribe_disconnect = None

    def value(self, register: Register) -> Any:
        """Return a selected field's most recent decoded value."""
        return self.values.get(register.key)

    def is_fresh(self, register: Register) -> bool:
        """Reject cached values that have missed several polling opportunities."""
        interval = (
            self.fast_interval
            if register.address == 6564 and self.fast_interval
            else self.regular_interval
        )
        budget = max(3 * interval, 4 * (self.message_spacing + 2))
        return (
            monotonic() - self.last_success.get(register.key, float("-inf")) <= budget
        )

    def async_start(self) -> None:
        """Start after enabled entities have registered their field contexts."""
        subscribe = getattr(self.device.modbus_unit, "on_connection_lost", None)
        if subscribe is not None:
            self._unsubscribe_disconnect = subscribe(self._connection_lost)
        self._worker = self.hass.async_create_background_task(
            self._run(), f"{DOMAIN} polling"
        )

    def _connection_lost(self) -> None:
        self.disconnect_count += 1

    def _pacing_remaining(self, now: float) -> float:
        if self._last_operation_finished is None:
            return self.message_spacing
        return max(0.0, self.message_spacing - (now - self._last_operation_finished))

    def _fast_start(self, group: ReadGroup) -> float:
        # Reserve the dispatch slot; the transport still enforces minimum pacing.
        return group.due if group.failures else group.due - self._response_estimate

    def _regular_fits(self, fast: ReadGroup, now: float) -> bool:
        # A regular response, the next pacing gap, then the battery response.
        finish = (
            now
            + self._pacing_remaining(now)
            + self._response_estimate
            + self.message_spacing
            + self._response_estimate
        )
        return finish <= fast.due

    def _sync_groups(self) -> None:
        contexts = set(self.async_contexts())
        if contexts == self._contexts:
            return
        self._contexts = contexts
        fast = {
            r.key
            for r in self.device.registers
            if r.address == 6564 and r.key in contexts and self.fast_interval
        }
        previous = {tuple(g.reader.resolved_fields): g for g in self._groups}
        groups = []
        for keys, interval, is_fast in (
            (fast, self.fast_interval, True),
            (contexts - fast, self.regular_interval, False),
        ):
            for reader in self.device.read_groups(keys):
                identity = tuple(reader.resolved_fields)
                groups.append(
                    previous.get(identity) or ReadGroup(reader, interval, is_fast)
                )
        self._groups = groups

    async def _async_update_data(self) -> UpdateReport:
        try:
            await self.device.async_ensure_setup()
        except (ModbusError, ValueError) as err:
            raise UpdateFailed(str(err)) from err
        if self._worker is not None:
            self._sync_groups()
            futures = []
            for group in self._groups:
                done = self.hass.loop.create_future()
                self._reads.append(Job(group, done))
                futures.append(done)
            self._wake.set()
            await asyncio.gather(*futures)
        return self._report

    async def async_write(self, register: Register, value: float) -> None:
        """Prioritize a write and read back only its field, without replaying writes."""
        if self._shutdown_requested or self._worker is None or self._worker.done():
            raise UpdateFailed("Device polling has stopped")
        (reader,) = self.device.read_groups([register.key])
        done = self.hass.loop.create_future()
        self._writes.append(
            Job(ReadGroup(reader, self.regular_interval), done, register, value)
        )
        self._wake.set()
        await done

    async def _read(self, group: ReadGroup) -> ModbusError | None:
        keys = set(group.reader.resolved_fields)
        start = monotonic()
        expected_pacing = self._pacing_remaining(start)
        deadline = group.due
        error = None
        try:
            await group.reader.async_update(notify=False)
        except (ModbusError, ValueError) as err:
            error = err if isinstance(err, ModbusError) else ModbusError(str(err))
            self._report.updated.difference_update(keys)
            self._report.failed.update(dict.fromkeys(keys, error))
        else:
            for key in keys:
                self.values[key] = getattr(group.reader, key)
                self.last_success[key] = monotonic()
                self._report.failed.pop(key, None)
            self._report.updated.update(keys)
            now = monotonic()
            if group.last_success is not None:
                group.gaps.append(now - group.last_success)
            group.last_success = now
            group.successes += 1
        finally:
            finished = monotonic()
            duration = finished - start
            self._last_operation_finished = finished
            if deadline and group.fast:
                group.lateness.append(max(0.0, finished - deadline))
            if error:
                group.errors += 1
            else:
                # This residual is a scheduling estimate, NOT measured wire latency.
                residual = max(0.05, min(2.0, duration - expected_pacing))
                self._response_estimate = 0.8 * self._response_estimate + 0.2 * residual
            self.read_durations.append(duration)
            group.failures = min(group.failures + 1, 6) if error else 0
            retry_interval = (
                max(group.interval, min(300, 5 * 2 ** (group.failures - 1)))
                if error
                else group.interval
            )
            if group.fast and not error:
                # Keep cadence anchored; skip missed slots without catch-up bursts.
                target = (
                    deadline + group.interval if deadline else finished + group.interval
                )
                earliest = finished + self.message_spacing + self._response_estimate
                if target <= earliest:
                    target += (
                        int((earliest - target) // group.interval) + 1
                    ) * group.interval
                group.due = target
            else:
                group.due = finished + retry_interval
            _LOGGER.debug(
                "Read %s took %.3fs including pacing/recovery; success=%s",
                sorted(keys),
                duration,
                error is None,
            )
        self.async_set_updated_data(self._report)
        return error

    async def _run(self) -> None:
        active: Job | None = None
        try:
            while not self._shutdown_requested:
                self._wake.clear()
                self._sync_groups()
                # At least one regular request gets a turn between fast reads.
                now = monotonic()
                due = [g for g in self._groups if not g.fast and g.due <= now]
                fast = next((g for g in self._groups if g.fast), None)
                fast_ready = fast is not None and self._fast_start(fast) <= now
                regular = min(
                    (g for g in due if not g.fast), key=lambda g: g.due, default=None
                )
                if self._writes:
                    active = self._writes.popleft()
                elif fast_ready and (
                    not self._last_fast or (regular is None and not self._reads)
                ):
                    await self._read(fast)
                    self._last_fast = True
                    continue
                elif self._reads and (
                    fast is None
                    or self._last_fast
                    or fast.failures
                    or self._regular_fits(fast, now)
                ):
                    active = self._reads.popleft()
                elif regular is not None and (
                    fast is None
                    or self._last_fast
                    or fast.failures
                    or self._regular_fits(fast, now)
                ):
                    await self._read(regular)
                    self._last_fast = False
                    continue
                else:
                    # Overdue regular groups may be intentionally held for fast.
                    deadlines = [
                        g.due for g in self._groups if not g.fast and g.due > now
                    ]
                    if fast is not None:
                        deadlines.append(self._fast_start(fast))
                    delay = max(0.001, min(deadlines, default=now + 1) - now)
                    try:
                        async with asyncio.timeout(min(delay, 1)):
                            await self._wake.wait()
                    except TimeoutError:
                        pass
                    continue
                if active.done.cancelled():
                    active = None
                    continue
                self.job_queue_waits.append(monotonic() - active.queued_at)
                try:
                    if active.register is not None:
                        try:
                            await self.device.async_write(active.register, active.value)
                        finally:
                            self._last_operation_finished = monotonic()
                    error = await self._read(active.group)
                    if error is not None and active.register is not None:
                        raise error
                except (ModbusError, ValueError, AttributeError) as err:
                    if not active.done.done():
                        active.done.set_exception(err)
                else:
                    if not active.done.done():
                        active.done.set_result(None)
                self._last_fast = active.group.fast
                active = None
        finally:
            for job in [*self._writes, *self._reads, *([active] if active else [])]:
                if not job.done.done():
                    job.done.cancel()
            self._writes.clear()
            self._reads.clear()

    async def async_shutdown(self) -> None:
        """Stop the worker before the integration releases its connection."""
        if self._unsubscribe_disconnect is not None:
            self._unsubscribe_disconnect()
            self._unsubscribe_disconnect = None
        await super().async_shutdown()
        if self._worker is not None:
            self._worker.cancel()
            await asyncio.gather(self._worker, return_exceptions=True)
            self._worker = None
