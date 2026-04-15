import pytest
import os
import time
import asyncio
from subsystems.phantom import Phantom
from core.message_bus import MessageBus, MessageEnvelope

@pytest.mark.asyncio
async def test_phantom_complexity_detection(tmp_path):
    bus = MessageBus()
    phantom = Phantom("SYS-08", bus)

    # Complex code (> 10 branches)
    code = "if 1: pass\n" * 15
    test_file = tmp_path / "complex.py"
    test_file.write_text(code)

    phantom.on_file_modified(str(test_file))

    findings = [f for f in phantom.findings if f["type"] == "COMPLEXITY"]
    assert len(findings) > 0
    assert findings[0]["file"] == str(test_file)

@pytest.mark.asyncio
async def test_phantom_test_gap_detection(tmp_path):
    bus = MessageBus()
    phantom = Phantom("SYS-08", bus)

    test_file = tmp_path / "new_module.py"
    test_file.write_text("def foo(): pass")

    phantom.on_file_modified(str(test_file))

    findings = [f for f in phantom.findings if f["type"] == "TEST_GAP"]
    assert len(findings) > 0
    assert "No corresponding test file" in findings[0]["issue"]

@pytest.mark.asyncio
async def test_phantom_message_processing():
    bus = MessageBus()
    phantom = Phantom("SYS-08", bus)
    bus.register_subsystem("USER")

    phantom.findings.append({"type": "MOCK", "issue": "test"})

    env = MessageEnvelope("M1", "USER", "SYS-08", "GET_FINDINGS", {}, 0, 3, "C1")
    await phantom.process_message(env)

    response = await bus.receive("USER")
    assert response.msg_type == "PHANTOM_FINDINGS"
    assert len(response.payload["findings"]) == 1
