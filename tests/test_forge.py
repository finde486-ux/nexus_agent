import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from subsystems.forge import Forge
from core.message_bus import MessageBus, MessageEnvelope
import uuid
import os
import asyncio

@pytest.mark.asyncio
async def test_forge_pipeline_execution():
    bus = MessageBus()
    forge = Forge("SYS-04", bus)

    # Register dependencies
    bus.register_subsystem("SYS-03") # NERVE
    bus.register_subsystem("SYS-07") # SENTINEL
    bus.register_subsystem("SYS-05") # ADVERSARY
    bus.register_subsystem("SYS-06") # OMNIROUTER

    # Mock NERVE budget
    async def mock_nerve_response():
        msg = await bus.receive("SYS-03")
        if msg:
            await bus.send(MessageEnvelope(
                str(uuid.uuid4()), "SYS-03", "SYS-04", "BUDGET_RESPONSE",
                {"budget": {"max_ram_bytes": 1024, "max_cpu_cores": 1}}, 0, 1, msg.msg_id
            ))

    # Mock SENTINEL scan
    async def mock_sentinel_response():
        msg = await bus.receive("SYS-07")
        if msg:
            await bus.send(MessageEnvelope(
                str(uuid.uuid4()), "SYS-07", "SYS-04", "SCAN_RESULT",
                {"status": "CLEAN"}, 0, 1, msg.msg_id
            ))

    # Mock ADVERSARY attack
    async def mock_adversary_response():
        msg = await bus.receive("SYS-05")
        if msg:
            await bus.send(MessageEnvelope(
                str(uuid.uuid4()), "SYS-05", "SYS-04", "ATTACK_RESULT",
                {"status": "CLEARED"}, 0, 1, msg.msg_id
            ))

    # Mock OMNIROUTER LLM calls
    async def mock_omnirouter_response():
        while True:
            msg = await bus.receive("SYS-06")
            if msg:
                await bus.send(MessageEnvelope(
                    str(uuid.uuid4()), "SYS-06", "SYS-04", "LLM_RESPONSE",
                    {"status": "success", "response": {"choices": [{"message": {"content": "{}"}}]}},
                    0, 1, msg.msg_id
                ))

    asyncio.create_task(mock_nerve_response())
    asyncio.create_task(mock_sentinel_response())
    asyncio.create_task(mock_adversary_response())
    asyncio.create_task(mock_omnirouter_response())

    with patch("docker.from_env") as mock_docker:
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        mock_client.containers.run.return_value = b"hello from nexus"

        env = MessageEnvelope("M1", "USER", "SYS-04", "TASK_REQUEST", {"task_id": "T1", "description": "test"}, 0, 3, "C1")
        bus.register_subsystem("USER")

        # Manually run task execution
        await forge.execute_task(env)

        response = await bus.receive("USER")
        assert response is not None
        assert response.msg_type == "TASK_COMPLETE"
        assert response.payload["task_id"] == "T1"
