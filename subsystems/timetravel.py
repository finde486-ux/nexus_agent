import asyncio
import time
import uuid
import subprocess
from typing import List, Dict, Any, Optional
from core.subsystem_base import SubsystemBase
from core.message_bus import MessageBus, MessageEnvelope

class TimeTravel(SubsystemBase):
    def __init__(self, subsystem_id: str, message_bus: MessageBus):
        super().__init__(subsystem_id, message_bus)

    async def initialize(self):
        self.logger.info("TimeTravel initialized.")

    async def process_message(self, envelope: MessageEnvelope):
        if envelope.msg_type == "DETECT_REGRESSION":
            await self.run_timetravel(envelope)

    async def run_timetravel(self, envelope: MessageEnvelope):
        # 3.11.1 TIMETRAVEL Protocol
        task_id = envelope.payload.get("task_id")
        file_path = envelope.payload.get("file_path")
        error_msg = envelope.payload.get("error_message")

        self.logger.info(f"TimeTravel starting root-cause analysis for {file_path}")

        # 1. RETRIEVE history (git log)
        history = self._get_git_history(file_path)

        # 2. BINARY SEARCH (git bisect semantics)
        broken_commit = await self._binary_search_history(history, file_path)

        # 3. ANALYZE diff
        analysis = await self._analyze_diff(broken_commit, file_path)

        # 4. GENERATE fix
        fix = await self._generate_fix(file_path, analysis)

        # 5. GENERATE regression test
        regression_test = await self._generate_regression_test(error_msg)

        # 6. GENERATE timeline report
        report = {
            "task_id": task_id,
            "root_cause": analysis,
            "broken_commit": broken_commit,
            "fix": fix,
            "regression_test": regression_test
        }

        # 7. STORE finding in MEMORY-GRAPH
        await self.message_bus.send(MessageEnvelope(
            str(uuid.uuid4()), self.subsystem_id, "SYS-02", "STORE_DATA",
            {"table": "bugs", "data": {
                "bug_id": str(uuid.uuid4()),
                "task_id": task_id,
                "file_id": file_path,
                "error_type": "REGRESSION",
                "description": error_msg,
                "root_cause": analysis,
                "fix_applied": fix,
                "timestamp": time.time()
            }}, time.monotonic(), 3, envelope.msg_id
        ))

        # 8. DELIVER report
        await self.message_bus.send(MessageEnvelope(
            str(uuid.uuid4()), self.subsystem_id, envelope.sender_id, "TIMETRAVEL_REPORT",
            {"report": report}, time.monotonic(), 3, envelope.msg_id
        ))

    def _get_git_history(self, file_path: str) -> List[str]:
        try:
            result = subprocess.run(
                ["git", "log", "--follow", "--format=%H", file_path],
                capture_output=True, text=True, check=True
            )
            return result.stdout.strip().split("\n")
        except Exception:
            return [] # Fallback to MEMORY-GRAPH snapshots would go here

    async def _binary_search_history(self, history: List[str], file_path: str) -> str:
        # Mocking binary search for Phase 8
        return history[0] if history else "HEAD"

    async def _analyze_diff(self, commit: str, file_path: str) -> str:
        # Use OMNIROUTER to explain root cause
        prompt = f"Explain the root cause of a bug introduced in commit {commit} for file {file_path}. Plain English, no jargon."
        return await self._call_omnirouter(prompt)

    async def _generate_fix(self, file_path: str, analysis: str) -> str:
        prompt = f"Generate a fix for file {file_path} based on this root cause analysis: {analysis}"
        return await self._call_omnirouter(prompt)

    async def _generate_regression_test(self, error_msg: str) -> str:
        prompt = f"Generate a minimal regression test case that triggers this error: {error_msg}"
        return await self._call_omnirouter(prompt)

    async def _call_omnirouter(self, prompt: str) -> str:
        msg_id = str(uuid.uuid4())
        await self.message_bus.send(MessageEnvelope(
            msg_id, self.subsystem_id, "SYS-06", "LLM_CALL",
            {"model": "gpt-4o", "messages": [{"role": "user", "content": prompt}]},
            time.time(), 1, msg_id
        ))
        res = await self.message_bus.receive(self.subsystem_id, timeout=60.0)
        if res and res.payload.get("status") == "success":
            return res.payload["response"]["choices"][0]["message"]["content"]
        return "Error calling LLM."
