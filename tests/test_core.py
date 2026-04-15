import pytest
from core.task import Task, TaskClassification
from core.subsystem_base import SubsystemBase
from core.message_bus import MessageBus, MessageEnvelope
import asyncio

class MockSubsystem(SubsystemBase):
    async def initialize(self):
        self.initialized = True

    async def process_message(self, envelope: MessageEnvelope):
        self.last_msg = envelope

def test_task_creation():
    task = Task(
        task_id="T1",
        description="Test task",
        classification=TaskClassification.COMPLEX,
        metadata={}
    )
    assert task.task_id == "T1"
    assert task.classification == TaskClassification.COMPLEX

@pytest.mark.asyncio
async def test_subsystem_base():
    bus = MessageBus()
    sub = MockSubsystem("SYS-TEST", bus)
    await sub.initialize()
    assert sub.initialized

    # Start sub in background
    task = asyncio.create_task(sub.run())

    env = MessageEnvelope(
        msg_id="M1",
        sender_id="EXTERNAL",
        receiver_id="SYS-TEST",
        msg_type="TASK",
        payload={},
        timestamp=0,
        priority=3,
        correlation_id="C1"
    )

    await bus.send(env)
    await asyncio.sleep(0.1)
    assert sub.last_msg == env

    sub.stop()
    await task
