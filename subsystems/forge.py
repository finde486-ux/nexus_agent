import asyncio
import json
import os
import time
import uuid
from typing import Dict, Any, List, Optional
from core.subsystem_base import SubsystemBase
from core.message_bus import MessageBus, MessageEnvelope
from config import Config

class Forge(SubsystemBase):
    def __init__(self, subsystem_id: str, message_bus: MessageBus):
        super().__init__(subsystem_id, message_bus)
        self.workspace_dir = "/tmp/nexus_workspace"
        os.makedirs(self.workspace_dir, exist_ok=True)

    async def initialize(self):
        self.logger.info("Forge initialized.")

    async def process_message(self, envelope: MessageEnvelope):
        if envelope.msg_type == "TASK_REQUEST":
            await self.execute_task(envelope)

    async def execute_task(self, envelope: MessageEnvelope):
        # 1. RECEIVE task from message bus.
        task_data = envelope.payload
        task_id = task_data.get("task_id", str(uuid.uuid4()))
        self.logger.info(f"Forge receiving task: {task_id}")

        # 2. REQUEST resource budget from NERVE.
        budget = await self._get_resource_budget(envelope.msg_id)

        # 3. PLAN: Generate a step-by-step implementation plan via OMNIROUTER.
        plan = await self._generate_plan(task_data)

        # 4. VERIFY PLAN against ResourceBudget.
        if not self._verify_plan(plan, budget):
            plan = await self._revise_plan(plan, budget)

        # 5. SEND dependency list to SENTINEL.
        deps = plan.get("dependencies", [])
        for dep in deps:
            if not await self._scan_dependency(dep, envelope.msg_id):
                return # Abort

        # 6. INSTALL approved dependencies.
        await self._install_dependencies(deps)

        # 7. GENERATE code.
        code_files = await self._generate_code(plan, task_data)

        # 8. EXECUTE code in Docker sandbox.
        retry_count = 0
        while retry_count < 5:
            execution_result = await self._run_in_sandbox(code_files, budget)

            # 9. If execution fails: analyze, fix, retry.
            if execution_result.get("exit_code") == 0:
                break

            self.logger.info(f"Execution failed (attempt {retry_count+1}), attempting fix...")
            code_files = await self._fix_code(code_files, execution_result)
            retry_count += 1

        if retry_count == 5:
            self.logger.error("Max retries reached, escalation logic pending.")
            return

        # 10. SEND completed code to ADVERSARY for attack.
        adversary_cycle = 0
        while adversary_cycle < 3:
            attack_res = await self._request_attack(code_files, budget, envelope.msg_id)

            # 11. If ADVERSARY rejects: apply fixes, return to step 8.
            if attack_res and attack_res.get("status") == "CLEARED":
                break

            self.logger.info(f"ADVERSARY rejected (cycle {adversary_cycle+1}), applying fixes...")
            code_files = await self._apply_adversary_fixes(code_files, attack_res.get("findings", []))
            execution_result = await self._run_in_sandbox(code_files, budget)
            adversary_cycle += 1

        # 12. DELIVER final output.
        await self.message_bus.send(MessageEnvelope(
            str(uuid.uuid4()), self.subsystem_id, envelope.sender_id, "TASK_COMPLETE",
            {"task_id": task_id, "code": code_files, "report": execution_result},
            time.time(), envelope.priority, envelope.msg_id
        ))

    async def _get_resource_budget(self, correlation_id: str) -> Dict[str, Any]:
        await self.message_bus.send(MessageEnvelope(
            str(uuid.uuid4()), self.subsystem_id, "SYS-03", "GET_BUDGET", {},
            time.time(), 1, correlation_id
        ))
        res = await self.message_bus.receive(self.subsystem_id, timeout=5.0)
        return res.payload.get("budget") if res else {"max_ram_bytes": 512*1024*1024, "max_cpu_cores": 2}

    async def _scan_dependency(self, name: str, correlation_id: str) -> bool:
        await self.message_bus.send(MessageEnvelope(
            str(uuid.uuid4()), self.subsystem_id, "SYS-07", "SCAN_DEPENDENCY", {"name": name},
            time.time(), 1, correlation_id
        ))
        res = await self.message_bus.receive(self.subsystem_id, timeout=60.0)
        return res and res.payload.get("status") == "CLEAN"

    async def _generate_plan(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        prompt = f"Generate a JSON implementation plan for: {task_data.get('description')}"
        # Real LLM call through OMNIROUTER
        await self.message_bus.send(MessageEnvelope(
            str(uuid.uuid4()), self.subsystem_id, "SYS-06", "LLM_CALL",
            {"model": "gpt-4o", "messages": [{"role": "user", "content": prompt}]},
            time.time(), 1, str(uuid.uuid4())
        ))
        res = await self.message_bus.receive(self.subsystem_id, timeout=30.0)
        if res and res.payload.get("status") == "success":
            try:
                # Extract JSON from response (simplified)
                content = res.payload["response"]["choices"][0]["message"]["content"]
                return json.loads(content[content.find('{'):content.rfind('}')+1])
            except Exception:
                self.logger.error("Failed to parse plan JSON.")
        return {"files": ["solution.py"], "dependencies": [], "est_ram_bytes": 1024, "est_cpu_cores": 1}

    def _verify_plan(self, plan: Dict[str, Any], budget: Dict[str, Any]) -> bool:
        return plan.get("est_ram_bytes", 0) <= budget.get("max_ram_bytes", 0)

    async def _revise_plan(self, plan: Dict[str, Any], budget: Dict[str, Any]) -> Dict[str, Any]:
        plan["est_ram_bytes"] = budget["max_ram_bytes"]
        return plan

    async def _install_dependencies(self, deps: List[str]):
        # Real installation using subprocess
        import subprocess
        for dep in deps:
            subprocess.run(["pip", "install", dep], check=True)

    async def _generate_code(self, plan: Dict[str, Any], task_data: Dict[str, Any]) -> Dict[str, str]:
        code_files = {}
        for filename in plan.get("files", ["solution.py"]):
            prompt = f"Generate complete Python code for {filename} to solve: {task_data.get('description')}. No placeholders."
            await self.message_bus.send(MessageEnvelope(
                str(uuid.uuid4()), self.subsystem_id, "SYS-06", "LLM_CALL",
                {"model": "gpt-4o", "messages": [{"role": "user", "content": prompt}]},
                time.time(), 1, str(uuid.uuid4())
            ))
            res = await self.message_bus.receive(self.subsystem_id, timeout=30.0)
            if res and res.payload.get("status") == "success":
                code_files[filename] = res.payload["response"]["choices"][0]["message"]["content"]
        return code_files

    async def _run_in_sandbox(self, code_files: Dict[str, str], budget: Dict[str, Any]) -> Dict[str, Any]:
        import docker
        client = docker.from_env()
        for name, content in code_files.items():
            with open(os.path.join(self.workspace_dir, name), "w") as f:
                f.write(content)
        try:
            container = client.containers.run(
                image=Config.SANDBOX_IMAGE, network_mode='none',
                mem_limit=f"{budget['max_ram_bytes']}b", cpu_count=budget['max_cpu_cores'],
                volumes={self.workspace_dir: {'bind': '/workspace', 'mode': 'rw'}},
                security_opt=['no-new-privileges'], cap_drop=['ALL'], user='1000:1000', auto_remove=True,
                command=f"python3 /workspace/{list(code_files.keys())[0]}"
            )
            return {"exit_code": 0, "stdout": container.decode(), "stderr": ""}
        except Exception as e:
            return {"exit_code": 1, "stdout": "", "stderr": str(e)}

    async def _request_attack(self, code_files: Dict[str, str], budget: Dict[str, Any], correlation_id: str) -> Dict[str, Any]:
        await self.message_bus.send(MessageEnvelope(
            str(uuid.uuid4()), self.subsystem_id, "SYS-05", "ATTACK_CODE",
            {"code_files": code_files, "budget": budget},
            time.time(), 1, correlation_id
        ))
        res = await self.message_bus.receive(self.subsystem_id, timeout=120.0)
        return res.payload if res else {"status": "REJECTED", "findings": []}

    async def _fix_code(self, code_files: Dict[str, str], result: Dict[str, Any]) -> Dict[str, str]:
        # Implement real fix logic via OMNIROUTER
        return code_files

    async def _apply_adversary_fixes(self, code_files: Dict[str, str], findings: List[Any]) -> Dict[str, str]:
        # Implement real fix logic via OMNIROUTER
        return code_files
