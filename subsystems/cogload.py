import time
import uuid
from typing import Dict, Any, List
from core.subsystem_base import SubsystemBase
from core.message_bus import MessageBus, MessageEnvelope
from core.task import Task, TaskClassification

class CogLoad(SubsystemBase):
    def __init__(self, subsystem_id: str, message_bus: MessageBus):
        super().__init__(subsystem_id, message_bus)
        self.task_history: Dict[str, List[Dict[str, Any]]] = {}

    async def initialize(self):
        self.logger.info("CogLoad initialized.")

    async def process_message(self, envelope: MessageEnvelope):
        if envelope.msg_type == "CLASSIFY_TASK":
            classification = self.classify_task(envelope.payload)
            response = MessageEnvelope(
                msg_id=str(uuid.uuid4()),
                sender_id=self.subsystem_id,
                receiver_id=envelope.sender_id,
                msg_type="TASK_CLASSIFIED",
                payload={"classification": classification.name},
                timestamp=time.time(),
                priority=envelope.priority,
                correlation_id=envelope.msg_id
            )
            await self.message_bus.send(response)
        elif envelope.msg_type == "MONITOR_QUALITY":
            await self.handle_monitoring(envelope.payload)

    def classify_task(self, task_data: Dict[str, Any]) -> TaskClassification:
        # 3.10.1 Task Classification Rules
        description = task_data.get("description", "")
        tokens_est = task_data.get("tokens_est", 0)
        files_count = task_data.get("files_count", 0)
        has_security_impact = task_data.get("has_security_impact", False)
        needs_architecture = task_data.get("needs_architecture", False)

        # SIMPLE: Single function, < 50 tokens, no reasoning chain
        if tokens_est < 50 and files_count <= 1 and not needs_architecture and not has_security_impact:
            return TaskClassification.SIMPLE

        # MEDIUM: Multi-function, context of 1-3 files, moderate reasoning
        if files_count <= 3 and not needs_architecture and not has_security_impact:
            return TaskClassification.MEDIUM

        # COMPLEX: Multi-file, architecture decisions, security, or debate protocol
        return TaskClassification.COMPLEX

    async def handle_monitoring(self, monitor_data: Dict[str, Any]):
        # 3.10.2 Automatic Tier Escalation
        task_id = monitor_data.get("task_id")
        output = monitor_data.get("output", "")
        failed_tests = monitor_data.get("failed_tests", False)
        incomplete = monitor_data.get("incomplete", False)
        retries = monitor_data.get("retries", 0)

        should_escalate = False

        # 1. Model's output contains placeholder code
        placeholders = ["# TODO", "FIXME", "pass", "raise NotImplementedError", "..."]
        if any(p in output for p in placeholders):
            should_escalate = True

        # 2. Model's output fails ADVERSARY's correctness tests
        if failed_tests:
            should_escalate = True

        # 3. Model's output is incomplete
        if incomplete:
            should_escalate = True

        # 4. Task has already been retried twice
        if retries >= 2:
            should_escalate = True

        if should_escalate:
            self.logger.info(f"Escalating task {task_id} to COMPLEX.")
            escalation_msg = MessageEnvelope(
                msg_id=str(uuid.uuid4()),
                sender_id=self.subsystem_id,
                receiver_id="SYS-01", # CORTEX
                msg_type="ESCALATE_TASK",
                payload={"task_id": task_id, "target_tier": "COMPLEX"},
                timestamp=time.time(),
                priority=1,
                correlation_id=str(uuid.uuid4())
            )
            await self.message_bus.send(escalation_msg)
