"""Exercise scheduling with real decoding and a controlled clock/transport."""

import asyncio
from unittest.mock import patch

import pytest
from modbus_connection import IllegalDataAddressError, ModbusConnectionError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.indevolt_modbus.coordinator import IndevoltCoordinator
from custom_components.indevolt_modbus.vendor.indevolt_modbus import IndevoltDevice


async def ready(hass, unit, addresses, **options):
    entry = MockConfigEntry(domain="indevolt_modbus", data={}, options=options)
    entry.add_to_hass(hass)
    coordinator = IndevoltCoordinator(hass, entry, IndevoltDevice(unit))
    entry.runtime_data = coordinator
    await coordinator.async_refresh()
    registers = {r.address: r for r in coordinator.device.registers}
    for address in addresses:
        coordinator.async_add_listener(lambda: None, registers[address].key)
    unit.read_events.clear()
    return coordinator, registers


async def until(predicate):
    for _ in range(100):
        if predicate():
            return
        await asyncio.sleep(0)
    pytest.fail("Worker did not reach expected state")


async def test_fast_updates_publish_without_reading_soc(hass, unit, monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(
        "custom_components.indevolt_modbus.coordinator.monotonic", lambda: clock[0]
    )
    coordinator, registers = await ready(
        hass, unit, [6564, 7599], fast_poll_interval=2, message_spacing=1
    )
    coordinator.async_start()
    try:
        await until(lambda: len(unit.read_events) == 2)
        assert [r.address for r in unit.read_events] == [6564, 7599]
        unit.holding[6564] = 123
        clock[0] += 2
        coordinator._wake.set()
        await until(lambda: len(unit.read_events) == 3)
        assert unit.read_events[-1].address == 6564
        assert coordinator.value(registers[6564]) == 123
        assert coordinator.value(registers[7599]) == 76.5
        # A failed fast read affects only battery power; subsequent success recovers.
        unit.fail_read(6564, IllegalDataAddressError())
        clock[0] += 2
        coordinator._wake.set()
        await until(lambda: registers[6564].key in coordinator.data.failed)
        assert registers[7599].key in coordinator.data.updated
        unit.fail_read(6564, None)
        clock[0] += 60
        coordinator._wake.set()
        await until(lambda: registers[6564].key in coordinator.data.updated)
    finally:
        await coordinator.async_shutdown()


async def test_write_priority_readback_and_regular_fairness(hass, unit, monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(
        "custom_components.indevolt_modbus.coordinator.monotonic", lambda: clock[0]
    )
    coordinator, registers = await ready(
        hass, unit, [6564, 7599, 2250], fast_poll_interval=2, message_spacing=1
    )
    entered = asyncio.Event()
    release = asyncio.Event()
    original = coordinator._read
    seen = []

    async def read(group):
        addresses = [f.address for f in group.reader.resolved_fields.values()]
        seen.append(addresses)
        if len(seen) == 2:
            entered.set()
            await release.wait()
        return await original(group)

    with patch.object(coordinator, "_read", side_effect=read):
        coordinator.async_start()
        try:
            await entered.wait()
            assert seen[0] == [6564]
            clock[0] += 3
            command = asyncio.create_task(coordinator.async_write(registers[1142], 42))
            await asyncio.sleep(0)
            release.set()
            await command
            await until(lambda: len(seen) >= 5)
            # Only the current regular request precedes the command. Its readback
            # is followed by fast telemetry and then another regular request.
            assert seen[2] == [1142]
            assert seen[3] == [6564]
            assert seen[4] != [6564]
            assert unit.holding[1142] == 42
            assert coordinator.value(registers[1142]) == 42
        finally:
            await coordinator.async_shutdown()


async def test_failed_write_is_not_replayed(hass, unit):
    coordinator, registers = await ready(hass, unit, [])
    coordinator.async_start()
    try:
        with patch.object(
            coordinator.device,
            "async_write",
            side_effect=ModbusConnectionError("lost acknowledgement"),
        ) as write:
            with pytest.raises(ModbusConnectionError):
                await coordinator.async_write(registers[1142], 42)
            assert write.await_count == 1
        assert not unit.read_events
    finally:
        await coordinator.async_shutdown()


async def test_shutdown_cancels_pending_commands(hass, unit):
    coordinator, registers = await ready(hass, unit, [6564])
    entered = asyncio.Event()

    async def blocked(group):
        entered.set()
        await asyncio.Event().wait()

    with patch.object(coordinator, "_read", side_effect=blocked):
        coordinator.async_start()
        await entered.wait()
        command = asyncio.create_task(coordinator.async_write(registers[1142], 42))
        await asyncio.sleep(0)
        await coordinator.async_shutdown()
        with pytest.raises(asyncio.CancelledError):
            await command
        assert coordinator._worker is None


async def test_stale_fast_value_and_disabled_entity(hass, unit, monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(
        "custom_components.indevolt_modbus.coordinator.monotonic", lambda: clock[0]
    )
    coordinator, registers = await ready(
        hass, unit, [7599], fast_poll_interval=2, message_spacing=1
    )
    coordinator.async_start()
    try:
        await until(lambda: len(unit.read_events) == 1)
        assert unit.read_events[0].address == 7599
        # Configuring fast polling alone does not enable a disabled battery entity.
        assert not any(group.fast for group in coordinator._groups)
        assert not coordinator.is_fresh(registers[6564])
        unsubscribe = coordinator.async_add_listener(lambda: None, registers[6564].key)
        coordinator._wake.set()
        await until(lambda: coordinator.is_fresh(registers[6564]))
        clock[0] += 13
        assert not coordinator.is_fresh(registers[6564])
        assert coordinator.is_fresh(registers[7599])
        unsubscribe()
        coordinator._sync_groups()
        assert not any(group.fast for group in coordinator._groups)
    finally:
        await coordinator.async_shutdown()


async def test_fast_cadence_reserves_slot_and_records_disconnects(
    hass, unit, monkeypatch
):
    clock = [100.0]
    monkeypatch.setattr(
        "custom_components.indevolt_modbus.coordinator.monotonic", lambda: clock[0]
    )
    coordinator, _ = await ready(
        hass,
        unit,
        [6564, 7599, 2250, 1142],
        fast_poll_interval=5,
        scan_interval=120,
        message_spacing=2,
    )
    original = coordinator.device.modbus_unit.read_holding_registers
    last_finish = [clock[0]]

    async def paced_read(address, count):
        clock[0] = max(clock[0], last_finish[0] + 2) + 0.4
        last_finish[0] = clock[0]
        return await original(address, count)

    with patch.object(
        coordinator.device.modbus_unit, "read_holding_registers", paced_read
    ):
        coordinator.async_start()
        try:
            for _ in range(400):
                await asyncio.sleep(0)
                clock[0] += 0.1
                coordinator._wake.set()
                if len(unit.read_events) >= 10:
                    break
            fast = next(g for g in coordinator._groups if g.fast)
            assert fast.successes >= 5
            assert all(4.5 <= gap <= 5.5 for gap in fast.gaps)
            assert all(g.successes >= 1 for g in coordinator._groups)
            unit._conn.simulate_connection_lost()
            assert coordinator.disconnect_count == 1
        finally:
            await coordinator.async_shutdown()
        assert coordinator._unsubscribe_disconnect is None


async def test_slow_read_skips_missed_slots_and_failure_backs_off(
    hass, unit, monkeypatch
):
    clock = [100.0]
    monkeypatch.setattr(
        "custom_components.indevolt_modbus.coordinator.monotonic", lambda: clock[0]
    )
    coordinator, _ = await ready(hass, unit, [6564], fast_poll_interval=5)
    coordinator._sync_groups()
    group = coordinator._groups[0]
    group.due = 105

    async def slow_update(**kwargs):
        clock[0] = 117

    with patch.object(group.reader, "async_update", side_effect=slow_update):
        await coordinator._read(group)
    assert group.due == 120
    assert list(group.lateness) == [12]
    with patch.object(
        group.reader, "async_update", side_effect=IllegalDataAddressError()
    ):
        await coordinator._read(group)
    assert group.errors == 1
    assert group.due == 122
    assert coordinator._fast_start(group) == 122
    await coordinator.async_shutdown()
