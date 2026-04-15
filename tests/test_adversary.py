import pytest
from subsystems.adversary import Adversary
from core.message_bus import MessageBus, MessageEnvelope

@pytest.mark.asyncio
async def test_adversary_attack_cleared():
    bus = MessageBus()
    adv = Adversary("SYS-05", bus)

    payload = {
        "code_files": {"solution.py": "print('safe')"},
        "budget": {"max_ram_bytes": 1024}
    }

    result = await adv.run_attack_suite(payload)
    assert result["status"] == "CLEARED"
    assert len(result["findings"]) == 0

@pytest.mark.asyncio
async def test_adversary_security_violation():
    bus = MessageBus()
    adv = Adversary("SYS-05", bus)

    payload = {
        "code_files": {"solution.py": "import os\nos.system('rm -rf')"},
        "budget": {"max_ram_bytes": 1024}
    }

    result = await adv.run_attack_suite(payload)
    assert result["status"] == "REJECTED"
    assert any(f["module"] == "Security Scanner" for f in result["findings"])

@pytest.mark.asyncio
async def test_adversary_message_processing():
    bus = MessageBus()
    adv = Adversary("SYS-05", bus)
    bus.register_subsystem("SYS-04")

    env = MessageEnvelope("M1", "SYS-04", "SYS-05", "ATTACK_CODE", {"code_files": {}}, 0, 3, "C1")
    await adv.process_message(env)

    response = await bus.receive("SYS-04")
    assert response.msg_type == "ATTACK_RESULT"
    assert "status" in response.payload
