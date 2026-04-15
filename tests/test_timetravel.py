import pytest
from unittest.mock import AsyncMock, patch
from subsystems.timetravel import TimeTravel
from core.message_bus import MessageBus, MessageEnvelope
import uuid
import time
import asyncio

@pytest.mark.asyncio
async def test_timetravel_protocol_flow():
    bus = MessageBus()
    tt = TimeTravel("SYS-11", bus)

    # Register dependencies
    bus.register_subsystem("SYS-06") # OMNIROUTER
    bus.register_subsystem("SYS-02") # MEMORY-GRAPH
    bus.register_subsystem("USER")

    # Mock OMNIROUTER response
    async def mock_omnirouter():
        while True:
            msg = await bus.receive("SYS-06")
            if msg:
                await bus.send(MessageEnvelope(
                    str(uuid.uuid4()), "SYS-06", "SYS-11", "LLM_RESPONSE",
                    {"status": "success", "response": {"choices": [{"message": {"content": "Root cause analysis content"}}]}},
                    0, 1, msg.msg_id
                ))

    asyncio.create_task(mock_omnirouter())

    # Mock MEMORY-GRAPH response
    async def mock_memory_graph():
        while True:
            await bus.receive("SYS-02")

    asyncio.create_task(mock_memory_graph())

    env = MessageEnvelope("M1", "USER", "SYS-11", "DETECT_REGRESSION",
                          {"task_id": "T1", "file_path": "bug.py", "error_message": "crash"}, 0, 3, "C1")

    await tt.run_timetravel(env)

    response = await bus.receive("USER")
    assert response.msg_type == "TIMETRAVEL_REPORT"
    report = response.payload["report"]
    assert report["task_id"] == "T1"
    assert "root_cause" in report
    assert "fix" in report
    assert "regression_test" in report
