import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from subsystems.evolver import Evolver
from core.message_bus import MessageBus, MessageEnvelope
from config import Config
import uuid
import time
import asyncio

@pytest.mark.asyncio
async def test_evolver_protocol_flow():
    bus = MessageBus()
    evolver = Evolver("SYS-09", bus)

    # Register dependencies
    bus.register_subsystem("SYS-06") # OMNIROUTER
    bus.register_subsystem("SYS-05") # ADVERSARY
    bus.register_subsystem("USER")

    # Mock OMNIROUTER response
    async def mock_omnirouter():
        while True:
            msg = await bus.receive("SYS-06")
            if msg:
                await bus.send(MessageEnvelope(
                    str(uuid.uuid4()), "SYS-06", "SYS-09", "LLM_RESPONSE",
                    {"status": "success", "response": {"choices": [{"message": {"content": "print('evolved') # optimized"}}]}},
                    0, 1, msg.msg_id
                ))

    asyncio.create_task(mock_omnirouter())

    # Mock ADVERSARY response
    async def mock_adversary():
        while True:
            msg = await bus.receive("SYS-05")
            if msg:
                await bus.send(MessageEnvelope(
                    str(uuid.uuid4()), "SYS-05", "SYS-09", "ATTACK_RESULT",
                    {"status": "CLEARED"}, 0, 1, msg.msg_id
                ))

    asyncio.create_task(mock_adversary())

    env = MessageEnvelope("M1", "USER", "SYS-09", "EVOLVE_CODE", {"code": "print('orig')"}, 0, 3, "C1")

    with patch("docker.from_env") as mock_docker:
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        mock_client.containers.run.return_value = b"hello"

        # Run a single generation for the test
        await evolver.run_evolution(env)

    response = await bus.receive("USER")
    assert response.msg_type == "EVOLUTION_COMPLETE"
    assert "winner" in response.payload
    assert response.payload["winner"]["fitness"] > 0

def test_evolver_mutation_library():
    bus = MessageBus()
    evolver = Evolver("SYS-09", bus)
    assert len(evolver.mutation_library) >= 8
    assert "Loop unrolling" in evolver.mutation_library
