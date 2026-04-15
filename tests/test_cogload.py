import pytest
from subsystems.cogload import CogLoad
from core.message_bus import MessageBus, MessageEnvelope
from core.task import TaskClassification
import asyncio

@pytest.mark.asyncio
async def test_cogload_classification_simple():
    bus = MessageBus()
    cl = CogLoad("SYS-10", bus)

    task_data = {
        "description": "Fix a typo",
        "tokens_est": 10,
        "files_count": 1,
        "has_security_impact": False,
        "needs_architecture": False
    }

    assert cl.classify_task(task_data) == TaskClassification.SIMPLE

@pytest.mark.asyncio
async def test_cogload_classification_medium():
    bus = MessageBus()
    cl = CogLoad("SYS-10", bus)

    task_data = {
        "description": "Implement a new feature",
        "tokens_est": 200,
        "files_count": 3,
        "has_security_impact": False,
        "needs_architecture": False
    }

    assert cl.classify_task(task_data) == TaskClassification.MEDIUM

@pytest.mark.asyncio
async def test_cogload_classification_complex():
    bus = MessageBus()
    cl = CogLoad("SYS-10", bus)

    # Needs architecture
    assert cl.classify_task({"needs_architecture": True}) == TaskClassification.COMPLEX
    # Security impact
    assert cl.classify_task({"has_security_impact": True}) == TaskClassification.COMPLEX
    # Many files
    assert cl.classify_task({"files_count": 5}) == TaskClassification.COMPLEX

@pytest.mark.asyncio
async def test_cogload_escalation_placeholder():
    bus = MessageBus()
    cl = CogLoad("SYS-10", bus)
    bus.register_subsystem("SYS-01")

    monitor_data = {
        "task_id": "T1",
        "output": "def foo():\n    pass # TODO: implement"
    }

    await cl.handle_monitoring(monitor_data)

    escalation = await bus.receive("SYS-01")
    assert escalation.msg_type == "ESCALATE_TASK"
    assert escalation.payload["target_tier"] == "COMPLEX"

@pytest.mark.asyncio
async def test_cogload_20_tasks_verification():
    bus = MessageBus()
    cl = CogLoad("SYS-10", bus)

    tasks = [
        ({"tokens_est": 5, "files_count": 1}, TaskClassification.SIMPLE),
        ({"tokens_est": 100, "files_count": 1}, TaskClassification.MEDIUM),
        ({"tokens_est": 10, "files_count": 5}, TaskClassification.COMPLEX),
        ({"has_security_impact": True}, TaskClassification.COMPLEX),
        ({"needs_architecture": True}, TaskClassification.COMPLEX),
        ({"tokens_est": 40, "files_count": 1}, TaskClassification.SIMPLE),
        ({"tokens_est": 60, "files_count": 2}, TaskClassification.MEDIUM),
        ({"tokens_est": 1000, "files_count": 4}, TaskClassification.COMPLEX),
        ({"tokens_est": 10, "files_count": 0}, TaskClassification.SIMPLE),
        ({"tokens_est": 500, "files_count": 2}, TaskClassification.MEDIUM),
        ({"tokens_est": 1, "files_count": 10}, TaskClassification.COMPLEX),
        ({"has_security_impact": True, "tokens_est": 5}, TaskClassification.COMPLEX),
        ({"tokens_est": 20, "files_count": 1, "needs_architecture": True}, TaskClassification.COMPLEX),
        ({"tokens_est": 30, "files_count": 1}, TaskClassification.SIMPLE),
        ({"tokens_est": 45, "files_count": 1}, TaskClassification.SIMPLE),
        ({"tokens_est": 150, "files_count": 2}, TaskClassification.MEDIUM),
        ({"tokens_est": 300, "files_count": 3}, TaskClassification.MEDIUM),
        ({"tokens_est": 50, "files_count": 4}, TaskClassification.COMPLEX),
        ({"tokens_est": 49, "files_count": 1}, TaskClassification.SIMPLE),
        ({"tokens_est": 51, "files_count": 1}, TaskClassification.MEDIUM),
    ]

    for data, expected in tasks:
        assert cl.classify_task(data) == expected
