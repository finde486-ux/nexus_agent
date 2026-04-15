import pytest
from subsystems.sentinel import Sentinel
from core.message_bus import MessageBus, MessageEnvelope

@pytest.mark.asyncio
async def test_sentinel_dependency_scanning_clean():
    bus = MessageBus()
    sentinel = Sentinel("SYS-07", bus)

    payload = {"name": "requests", "version": "2.31.0"}
    result = await sentinel.scan_dependency(payload)
    assert result["status"] == "CLEAN"

@pytest.mark.asyncio
async def test_sentinel_dependency_scanning_malicious():
    bus = MessageBus()
    sentinel = Sentinel("SYS-07", bus)

    payload = {"name": "malicious-pkg"}
    result = await sentinel.scan_dependency(payload)
    assert result["status"] == "QUARANTINED"
    assert "Malware detected" in result["report"][0]

@pytest.mark.asyncio
async def test_sentinel_ast_scanner_violation():
    bus = MessageBus()
    sentinel = Sentinel("SYS-07", bus)

    # Code with security violation
    code = "import os\nos.system('rm -rf /')"

    bus.register_subsystem("SYS-04")
    env = MessageEnvelope("M1", "SYS-04", "SYS-07", "SCAN_CODE", {"code": code}, 0, 3, "C1")
    await sentinel.process_message(env)

    response = await bus.receive("SYS-04")
    assert response.msg_type == "CODE_SCAN_RESULT"
    violations = response.payload["violations"]
    assert any(v["type"] == "SECURITY_VIOLATION" for v in violations)
    assert any("system" in v["message"] for v in violations)

@pytest.mark.asyncio
async def test_sentinel_ast_scanner_secrets():
    bus = MessageBus()
    sentinel = Sentinel("SYS-07", bus)

    code = "AWS_SECRET = 'AKIAIOSFODNN7EXAMPLE'"
    violations = sentinel.scanner.scan(code)
    assert any("secret" in v["message"].lower() for v in violations)

@pytest.mark.asyncio
async def test_sentinel_10_malware_samples_verification():
    bus = MessageBus()
    sentinel = Sentinel("SYS-07", bus)

    # Planted "malware"
    malware_samples = ["malicious-pkg", "cryptominer-lib", "vulnerable-pkg"]
    for sample in malware_samples:
        result = await sentinel.scan_dependency({"name": sample})
        assert result["status"] == "QUARANTINED"
