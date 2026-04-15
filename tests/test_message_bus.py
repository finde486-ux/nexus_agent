import pytest
import asyncio
import time
import uuid
from core.message_bus import MessageBus, MessageEnvelope

@pytest.mark.asyncio
async def test_message_bus_registration():
    bus = MessageBus()
    bus.register_subsystem("SYS-01")
    assert "SYS-01" in bus.inboxes

@pytest.mark.asyncio
async def test_message_bus_send_receive():
    bus = MessageBus()
    bus.register_subsystem("SYS-01")
    bus.register_subsystem("SYS-02")

    env = MessageEnvelope(
        msg_id=str(uuid.uuid4()),
        sender_id="SYS-01",
        receiver_id="SYS-02",
        msg_type="TEST",
        payload={"data": "hello"},
        timestamp=time.time(),
        priority=1,
        correlation_id=str(uuid.uuid4())
    )

    await bus.send(env)
    received = await bus.receive("SYS-02")
    assert received == env

@pytest.mark.asyncio
async def test_message_bus_broadcast():
    bus = MessageBus()
    bus.register_subsystem("SYS-01")
    bus.register_subsystem("SYS-02")
    bus.register_subsystem("SYS-03")

    env = MessageEnvelope(
        msg_id=str(uuid.uuid4()),
        sender_id="SYS-01",
        receiver_id="BROADCAST",
        msg_type="TEST",
        payload={"data": "hello"},
        timestamp=time.time(),
        priority=1,
        correlation_id=str(uuid.uuid4())
    )

    await bus.send(env)
    r2 = await bus.receive("SYS-02")
    r3 = await bus.receive("SYS-03")
    assert r2 == env
    assert r3 == env

@pytest.mark.asyncio
async def test_message_bus_timeout():
    bus = MessageBus()
    bus.register_subsystem("SYS-01")
    received = await bus.receive("SYS-01", timeout=0.1)
    assert received is None

@pytest.mark.asyncio
async def test_message_bus_performance():
    bus = MessageBus()
    bus.register_subsystem("SENDER")
    bus.register_subsystem("RECEIVER")

    count = 1000
    start_time = time.perf_counter()

    for i in range(count):
        env = MessageEnvelope(
            msg_id=str(uuid.uuid4()),
            sender_id="SENDER",
            receiver_id="RECEIVER",
            msg_type="PERF",
            payload={"i": i},
            timestamp=time.time(),
            priority=3,
            correlation_id=str(uuid.uuid4())
        )
        await bus.send(env)

    for i in range(count):
        received = await bus.receive("RECEIVER", timeout=1.0)
        assert received is not None

    end_time = time.perf_counter()
    duration = end_time - start_time
    print(f"\nSent and received {count} messages in {duration:.4f}s ({count/duration:.2f} msg/s)")
    assert duration < 1.0 # Should easily handle 1000 msg/s
