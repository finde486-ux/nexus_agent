import asyncio
import json
import os
import time
import uuid
import re
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
        execution_result = {"exit_code": 1}
        while retry_count < 5:
            execution_result = await self._run_in_sandbox(code_files, budget)

            # 9. If execution fails: analyze, fix, retry.
            if execution_result.get("exit_code") == 0:
                break

            self.logger.info(f"Execution failed (attempt {retry_count+1}), attempting fix...")
            code_files = await self._fix_code(code_files, execution_result, task_data)
            retry_count += 1

        if retry_count == 5:
            self.logger.error("Max retries reached, escalating to CORTEX.")
            await self._escalate_to_cortex(task_id, task_data, envelope.msg_id)
            return

        # 10. SEND completed code to ADVERSARY for attack.
        adversary_cycle = 0
        while adversary_cycle < 3:
            attack_res = await self._request_attack(code_files, budget, envelope.msg_id)

            # 11. If ADVERSARY rejects: apply fixes, return to step 8.
            if attack_res and attack_res.get("status") == "CLEARED":
                break

            self.logger.info(f"ADVERSARY rejected (cycle {adversary_cycle+1}), applying fixes...")
            code_files = await self._apply_adversary_fixes(code_files, attack_res.get("findings", []), task_data)
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
        prompt = f"Generate a JSON implementation plan for: {task_data.get('description')}. Format: {{'files': ['file1.py'], 'dependencies': [], 'est_ram_bytes': N, 'est_cpu_cores': N}}"
        res = await self._call_llm(prompt)
        if res:
            try:
                match = re.search(r'\{.*\}', res, re.DOTALL)
                return json.loads(match.group(0)) if match else {}
            except Exception:
                self.logger.error("Failed to parse plan JSON.")
        return {"files": ["solution.py"], "dependencies": [], "est_ram_bytes": 1000000, "est_cpu_cores": 1}

    def _verify_plan(self, plan: Dict[str, Any], budget: Dict[str, Any]) -> bool:
        return plan.get("est_ram_bytes", 0) <= budget.get("max_ram_bytes", 1e9)

    async def _revise_plan(self, plan: Dict[str, Any], budget: Dict[str, Any]) -> Dict[str, Any]:
        plan["est_ram_bytes"] = budget.get("max_ram_bytes", 512*1024*1024)
        return plan

    async def _install_dependencies(self, deps: List[str]):
        import subprocess
        for dep in deps:
            try:
                subprocess.run(["pip", "install", dep], check=True, capture_output=True)
            except Exception as e:
                self.logger.error(f"Failed to install {dep}: {e}")

    async def _generate_code(self, plan: Dict[str, Any], task_data: Dict[str, Any]) -> Dict[str, str]:
        code_files = {}
        for filename in plan.get("files", ["solution.py"]):
            prompt = f"Generate complete Python code for {filename} to solve: {task_data.get('description')}. No placeholders."
            res = await self._call_llm(prompt)
            if res:
                code_files[filename] = res
        return code_files

    async def _run_in_sandbox(self, code_files: Dict[str, str], budget: Dict[str, Any]) -> Dict[str, Any]:
        import docker
        if not code_files: return {"exit_code": 1, "stderr": "No code files"}
        client = docker.from_env()
        for name, content in code_files.items():
            with open(os.path.join(self.workspace_dir, name), "w") as f:
                f.write(content)
        entry_point = list(code_files.keys())[0]
        try:
            container = client.containers.run(
                image=Config.SANDBOX_IMAGE, network_mode='none',
                mem_limit=f"{budget.get('max_ram_bytes', 512*1024*1024)}b", cpu_count=budget.get('max_cpu_cores', 2),
                volumes={self.workspace_dir: {'bind': '/workspace', 'mode': 'rw'}},
                security_opt=['no-new-privileges'], cap_drop=['ALL'], user='1000:1000', auto_remove=True,
                command=f"python3 /workspace/{entry_point}"
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

    async def _fix_code(self, code_files: Dict[str, str], result: Dict[str, Any], task_data: Dict[str, Any]) -> Dict[str, str]:
        prompt = f"The following code failed with error: {result.get('stderr')}\n\nTask: {task_data.get('description')}\n\nCode:\n{json.dumps(code_files)}\n\nProvide the fixed code for all files."
        res = await self._call_llm(prompt)
        # Simplified: in real impl we'd parse multi-file output
        if res:
            for k in code_files: code_files[k] = res
        return code_files

    async def _apply_adversary_fixes(self, code_files: Dict[str, str], findings: List[Any], task_data: Dict[str, Any]) -> Dict[str, str]:
        prompt = f"The following code failed ADVERSARY checks: {json.dumps(findings)}\n\nTask: {task_data.get('description')}\n\nCode:\n{json.dumps(code_files)}\n\nProvide the fixed code."
        res = await self._call_llm(prompt)
        if res:
            for k in code_files: code_files[k] = res
        return code_files

    async def _escalate_to_cortex(self, task_id: str, task_data: Dict[str, Any], correlation_id: str):
        await self.message_bus.send(MessageEnvelope(
            str(uuid.uuid4()), self.subsystem_id, "SYS-01", "SOLVE_COMPLEX_TASK",
            {"task_id": task_id, "description": task_data.get("description")},
            time.time(), 1, correlation_id
        ))

    async def _call_llm(self, prompt: str) -> Optional[str]:
        msg_id = str(uuid.uuid4())
        await self.message_bus.send(MessageEnvelope(
            msg_id, self.subsystem_id, "SYS-06", "LLM_CALL",
            {"model": "gpt-4o", "messages": [{"role": "user", "content": prompt}]},
            time.time(), 1, msg_id
        ))
        res = await self.message_bus.receive(self.subsystem_id, timeout=60.0)
        if res and res.payload.get("status") == "success":
            return res.payload["response"]["choices"][0]["message"]["content"]
        return None
