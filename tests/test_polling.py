"""Exercise scheduling with real decoding and a controlled clock/transport."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from indevolt_modbus import IndevoltDevice
from modbus_connection import IllegalDataAddressError, ModbusConnectionError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.indevolt_modbus.coordinator import IndevoltCoordinator


async def ready(hass, unit, addresses, disabled=False):
    entry = MockConfigEntry(
        domain="indevolt_modbus", data={}, pref_disable_polling=disabled
    )
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
    coordinator, registers = await ready(hass, unit, [1284, 7599])
    coordinator.async_start()
    try:
        await until(lambda: len(unit.read_events) == 2)
        assert [r.address for r in unit.read_events] == [1284, 7599]
        unit.holding[1284] = 123
        clock[0] += 10
        coordinator._wake.set()
        await until(lambda: len(unit.read_events) == 3)
        assert unit.read_events[-1].address == 1284
        assert coordinator.value(registers[1284]) == 123
        assert coordinator.value(registers[7599]) == 76.5
        # A failed AC read leaves SOC available.
        unit.fail_read(1284, IllegalDataAddressError())
        clock[0] += 10
        coordinator._wake.set()
        await until(lambda: registers[1284].key in coordinator.data.failed)
        assert registers[7599].key in coordinator.data.updated
        unit.fail_read(1284, None)
        clock[0] += 60
        coordinator._wake.set()
        await until(lambda: registers[1284].key in coordinator.data.updated)
    finally:
        await coordinator.async_shutdown()


async def test_write_priority_readback_and_regular_fairness(hass, unit, monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(
        "custom_components.indevolt_modbus.coordinator.monotonic", lambda: clock[0]
    )
    coordinator, registers = await ready(hass, unit, [1284, 7599, 2250])
    entered = asyncio.Event()
    release = asyncio.Event()
    original = coordinator._read
    seen = []

    async def read(group, **kwargs):
        addresses = [f.address for f in group.reader.resolved_fields.values()]
        seen.append(addresses)
        if len(seen) == 2:
            entered.set()
            await release.wait()
        return await original(group, **kwargs)

    with patch.object(coordinator, "_read", side_effect=read):
        coordinator.async_start()
        try:
            await entered.wait()
            assert seen[0] == [1284]
            clock[0] += 16
            command = asyncio.create_task(coordinator.async_write(registers[1142], 42))
            await asyncio.sleep(0)
            release.set()
            await command
            await until(lambda: len(seen) >= 5)
            # Only the current regular request precedes the command. Its readback
            # is followed by fast telemetry and then another regular request.
            assert seen[2] == [1142]
            assert seen[3] == [1284]
            assert seen[4] != [1284]
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
    coordinator, registers = await ready(hass, unit, [1284])
    entered = asyncio.Event()

    async def blocked(group, **kwargs):
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
    coordinator, registers = await ready(hass, unit, [7599])
    coordinator.async_start()
    try:
        await until(lambda: len(unit.read_events) == 1)
        assert unit.read_events[0].address == 7599
        # Disabled AC power has no polling group.
        assert not any(group.fast for group in coordinator._groups)
        assert not coordinator.is_fresh(registers[1284])
        unsubscribe = coordinator.async_add_listener(lambda: None, registers[1284].key)
        coordinator._wake.set()
        await until(lambda: coordinator.is_fresh(registers[1284]))
        clock[0] += 46
        assert not coordinator.is_fresh(registers[1284])
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
        [1284, 7599, 2250, 1142],
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
            for _ in range(1800):
                await asyncio.sleep(0)
                clock[0] += 0.1
                coordinator._wake.set()
                if len(unit.read_events) >= 16:
                    break
            fast = next(g for g in coordinator._groups if g.fast)
            assert fast.successes >= 5
            assert all(9.5 <= gap <= 10.5 for gap in fast.gaps)
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
    coordinator, _ = await ready(hass, unit, [1284])
    coordinator._sync_groups()
    group = coordinator._groups[0]
    group.due = 110

    async def slow_update(**kwargs):
        clock[0] = 147

    with patch.object(group.reader, "async_update", side_effect=slow_update):
        await coordinator._read(group)
    assert group.due == 150
    assert list(group.lateness) == [37]
    with patch.object(
        group.reader, "async_update", side_effect=IllegalDataAddressError()
    ):
        await coordinator._read(group)
    assert group.errors == 1
    assert group.due == 157
    assert coordinator._fast_start(group) == 157
    await coordinator.async_shutdown()


async def test_polling_disabled_allows_only_explicit_refresh_and_writes(hass, unit):
    coordinator, registers = await ready(hass, unit, [1284, 7599], disabled=True)
    coordinator.async_start()
    try:
        await hass.async_block_till_done()
        assert not unit.read_events
        await coordinator.async_refresh()
        assert {event.address for event in unit.read_events} == {1284, 7599}
        unit.read_events.clear()
        await coordinator.async_write(registers[1142], 42)
        assert [event.address for event in unit.read_events] == [1142]
        assert unit.holding[1142] == 42
        unit.read_events.clear()
        await hass.async_block_till_done()
        assert not unit.read_events
    finally:
        await coordinator.async_shutdown()


async def test_removing_last_listener_pauses_and_adding_resumes(
    hass, unit, monkeypatch
):
    clock = [100.0]
    monkeypatch.setattr(
        "custom_components.indevolt_modbus.coordinator.monotonic", lambda: clock[0]
    )
    coordinator, registers = await ready(hass, unit, [])
    coordinator.async_start()
    unsubscribe = coordinator.async_add_listener(lambda: None, registers[1284].key)
    try:
        await until(lambda: len(unit.read_events) == 1)
        unsubscribe()
        await hass.async_block_till_done()
        assert coordinator._groups == []
        unit.read_events.clear()
        clock[0] += 120
        coordinator._wake.set()
        await hass.async_block_till_done()
        assert not unit.read_events
        unsubscribe = coordinator.async_add_listener(lambda: None, registers[1284].key)
        await until(lambda: len(unit.read_events) == 1)
        assert unit.read_events[0].address == 1284
    finally:
        unsubscribe()
        await coordinator.async_shutdown()


async def test_renamed_ac_entity_keeps_fixed_cadence(hass, unit):

    from homeassistant.helpers import entity_registry as er

    entry = MockConfigEntry(
        domain="indevolt_modbus",
        data={"host": "192.0.2.10", "port": 8899, "unit_id": 1},
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.indevolt_modbus.async_get_unit", AsyncMock(return_value=unit)
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        registry = er.async_get(hass)
        entity_id = registry.async_get_entity_id(
            "sensor", "indevolt_modbus", f"{entry.entry_id}_acout_w_1284"
        )
        registry.async_update_entity(entity_id, new_entity_id="sensor.renamed_ac")
        await hass.async_block_till_done()
        coordinator = entry.runtime_data
        coordinator._sync_groups()
        fast = next(group for group in coordinator._groups if group.fast)
        assert list(fast.reader.resolved_fields) == ["acout_w_1284"]
        assert fast.interval == 10
        assert {group.interval for group in coordinator._groups} == {10, 60, 300, 3600}
        assert await hass.config_entries.async_unload(entry.entry_id)


async def test_manual_refresh_does_not_postpone_next_ac_slot(hass, unit, monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(
        "custom_components.indevolt_modbus.coordinator.monotonic", lambda: clock[0]
    )
    coordinator, _ = await ready(hass, unit, [1284])
    coordinator.async_start()
    try:
        await until(lambda: len(unit.read_events) == 1)
        group = coordinator._groups[0]
        assert group.due == 110
        clock[0] = 105
        await coordinator.async_refresh()
        assert group.due == 110
        assert len(unit.read_events) == 2
        clock[0] = 110
        coordinator._wake.set()
        await until(lambda: len(unit.read_events) == 3)
        assert group.due == 120
    finally:
        await coordinator.async_shutdown()


async def test_ha_shutdown_cancels_worker_and_queued_operations(hass, unit):
    coordinator, registers = await ready(hass, unit, [1284])
    entered = asyncio.Event()

    async def blocked(group, **kwargs):
        entered.set()
        await asyncio.Event().wait()

    with patch.object(coordinator, "_read", side_effect=blocked):
        coordinator.async_start()
        worker = coordinator._worker
        await entered.wait()
        command = asyncio.create_task(coordinator.async_write(registers[1142], 42))
        refresh = asyncio.create_task(coordinator.async_refresh())
        await until(lambda: bool(coordinator._writes and coordinator._reads))
        await hass.async_stop()
        with pytest.raises(asyncio.CancelledError):
            await command
        await refresh
        assert refresh.done()
        assert not coordinator._reads
        assert worker.cancelled()
        assert coordinator._unsubscribe_disconnect is None
        assert not unit.read_events


async def test_regular_field_waits_sixty_seconds_after_completion(
    hass, unit, monkeypatch
):
    clock = [100.0]
    monkeypatch.setattr(
        "custom_components.indevolt_modbus.coordinator.monotonic", lambda: clock[0]
    )
    coordinator, _ = await ready(hass, unit, [7599])
    coordinator.async_start()
    try:
        await until(lambda: len(unit.read_events) == 1)
        clock[0] = 115
        coordinator._wake.set()
        await hass.async_block_till_done()
        assert len(unit.read_events) == 1
        clock[0] = 160
        coordinator._wake.set()
        await until(lambda: len(unit.read_events) == 2)
        assert unit.read_events[-1].address == 7599
        assert coordinator._groups[0].due == 220
    finally:
        await coordinator.async_shutdown()


@pytest.mark.parametrize(
    ("address", "interval"),
    [
        (1284, 10),
        (7599, 60),
        (6564, 60),
        (124, 60),
        (140, 60),
        (1246, 60),
        (1247, 60),
        (1132, 60),
        (1133, 60),
        (1134, 60),
        (1142, 300),
        (1144, 300),
        (1151, 300),
        (7265, 300),
        (7266, 300),
        (70, 3600),
        (7534, 3600),
        (89, 3600),
        (78, 3600),
    ],
)
async def test_tier_classification_and_freshness(
    hass, unit, monkeypatch, address, interval
):
    clock = [100.0]
    monkeypatch.setattr(
        "custom_components.indevolt_modbus.coordinator.monotonic", lambda: clock[0]
    )
    coordinator, registers = await ready(hass, unit, [address])
    register = registers[address]
    coordinator._sync_groups()
    assert coordinator._groups[0].interval == interval
    coordinator.last_success[register.key] = clock[0]
    clock[0] += 3 * interval
    assert coordinator.is_fresh(register)
    clock[0] += 1
    assert not coordinator.is_fresh(register)
    await coordinator.async_shutdown()


async def test_four_tiers_read_initially_and_repeat_at_their_own_intervals(
    hass, unit, monkeypatch
):
    clock = [100.0]
    monkeypatch.setattr(
        "custom_components.indevolt_modbus.coordinator.monotonic", lambda: clock[0]
    )
    coordinator, _ = await ready(hass, unit, [1284, 7599, 1142, 89])
    coordinator.async_start()
    try:
        await until(lambda: len(unit.read_events) == 4)
        assert [event.address for event in unit.read_events] == [1284, 7599, 1142, 89]
        unit.read_events.clear()
        clock[0] = 110
        coordinator._wake.set()
        await until(lambda: len(unit.read_events) == 1)
        assert [event.address for event in unit.read_events] == [1284]
        unit.read_events.clear()
        clock[0] = 160
        coordinator._wake.set()
        await until(lambda: len(unit.read_events) == 2)
        assert {event.address for event in unit.read_events} == {1284, 7599}
        unit.read_events.clear()
        clock[0] = 400
        coordinator._wake.set()
        await until(lambda: len(unit.read_events) == 3)
        assert {event.address for event in unit.read_events} == {1284, 7599, 1142}
        unit.read_events.clear()
        clock[0] = 3700
        coordinator._wake.set()
        await until(lambda: len(unit.read_events) == 4)
        assert {event.address for event in unit.read_events} == {1284, 7599, 1142, 89}
    finally:
        await coordinator.async_shutdown()


async def test_manual_refresh_includes_settings_and_information(
    hass, unit, monkeypatch
):
    clock = [100.0]
    monkeypatch.setattr(
        "custom_components.indevolt_modbus.coordinator.monotonic", lambda: clock[0]
    )
    coordinator, registers = await ready(hass, unit, [1284, 7599, 1142, 89])
    coordinator.async_start()
    try:
        await until(lambda: len(unit.read_events) == 4)
        unit.read_events.clear()
        unit.holding[89] = 5000
        unit.holding[1142] = 30
        clock[0] = 104
        await coordinator.async_refresh()
        assert {event.address for event in unit.read_events} == {1284, 7599, 1142, 89}
        assert coordinator.value(registers[89]) == 5000
        assert coordinator.value(registers[1142]) == 30
        unit.read_events.clear()
        await coordinator.async_write(registers[1142], 40)
        assert [event.address for event in unit.read_events] == [1142]
        assert coordinator.value(registers[1142]) == 40
    finally:
        await coordinator.async_shutdown()


async def test_one_hour_paced_workload_keeps_ac_cadence_without_starving_slower_tiers(
    hass, unit, monkeypatch
):
    clock = [100.0]
    monkeypatch.setattr(
        "custom_components.indevolt_modbus.coordinator.monotonic", lambda: clock[0]
    )
    coordinator, _ = await ready(
        hass,
        unit,
        [
            89,
            124,
            174,
            1269,
            1271,
            1284,
            2250,
            6563,
            6564,
            7512,
            7519,
            7521,
            7553,
            7599,
            1138,
            1142,
            1146,
            1147,
            1151,
            1152,
            1144,
            1150,
            7265,
            1143,
            7266,
        ],
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
            while clock[0] < 3800:
                await asyncio.sleep(0)
                clock[0] += 0.1
                coordinator._wake.set()
            await hass.async_block_till_done()
            fast = next(group for group in coordinator._groups if group.fast)
            assert fast.successes >= 360
            assert sum(fast.gaps) / len(fast.gaps) == pytest.approx(10, abs=0.05)
            assert min(fast.gaps) >= 8.5
            assert max(fast.gaps) <= 11.5
            for group in coordinator._groups:
                assert group.errors == 0
                assert (
                    group.successes
                    >= {10: 360, 60: 50, 300: 10, 3600: 2}[group.interval]
                )
        finally:
            await coordinator.async_shutdown()
