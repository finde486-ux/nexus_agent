import pytest
import os
import time
from subsystems.immune import Immune, ModuleHealth
from core.message_bus import MessageBus, MessageEnvelope

@pytest.mark.asyncio
async def test_immune_pbs_calculation():
    bus = MessageBus()
    immune = Immune("SYS-12", bus)

    health = ModuleHealth(
        churn_norm=0.5,
        complexity_norm=0.8,
        coupling_norm=0.3,
        coverage=0.7,
        history_norm=0.2
    )

    score = immune.predicted_bug_score(health)
    # 0.5*0.3 + 0.8*0.25 + 0.3*0.2 + (1-0.7)*0.15 + 0.2*0.1
    # 0.15 + 0.20 + 0.06 + 0.045 + 0.02 = 0.475
    assert 0.47 < score < 0.48

@pytest.mark.asyncio
async def test_immune_report_generation():
    bus = MessageBus()
    immune = Immune("SYS-12", bus)
    bus.register_subsystem("USER")

    await immune.generate_daily_report()

    date_str = time.strftime("%Y-%m-%d")
    report_path = os.path.join(".nexus/health_reports", f"{date_str}.md")
    assert os.path.exists(report_path)

    with open(report_path, "r") as f:
        content = f.read()
        assert "Overall Health Score" in content
        assert "Active Infections" in content
        # Ensure at least 3 findings are present (Phase 7 Exit Criteria)
        assert content.count("- **") + content.count("1. subsystems/") >= 3

@pytest.mark.asyncio
async def test_immune_broadcast_notification():
    bus = MessageBus()
    immune = Immune("SYS-12", bus)
    bus.register_subsystem("RECEIVER")

    # Send broadcast
    await immune.generate_daily_report()

    # Check if receiver got it
    response = await bus.receive("RECEIVER", timeout=1.0)
    assert response.msg_type == "HEALTH_REPORT_GENERATED"
