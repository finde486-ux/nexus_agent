import pytest
from subsystems.nerve import Nerve, ResourceBudget
from core.message_bus import MessageBus, MessageEnvelope
import asyncio

@pytest.mark.asyncio
async def test_nerve_telemetry():
    bus = MessageBus()
    nerve = Nerve("SYS-03", bus)
    telemetry = nerve.get_telemetry()
    assert "cpu_usage" in telemetry
    assert "ram_available" in telemetry
    assert telemetry["ram_available"] > 0

@pytest.mark.asyncio
async def test_nerve_budget_assignment():
    bus = MessageBus()
    nerve = Nerve("SYS-03", bus)
    budget = nerve.compute_budget()
    assert isinstance(budget, ResourceBudget)
    assert budget.max_ram_bytes > 0
    assert budget.max_cpu_cores >= 1

@pytest.mark.asyncio
async def test_nerve_message_processing():
    bus = MessageBus()
    nerve = Nerve("SYS-03", bus)
    bus.register_subsystem("SYS-04")

    env = MessageEnvelope("M1", "SYS-04", "SYS-03", "GET_BUDGET", {}, 0, 3, "C1")
    await nerve.process_message(env)

    response = await bus.receive("SYS-04")
    assert response.msg_type == "BUDGET_RESPONSE"
    assert "budget" in response.payload
