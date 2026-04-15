import asyncio
import time
import uuid
import json
import re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from core.subsystem_base import SubsystemBase
from core.message_bus import MessageBus, MessageEnvelope

@dataclass
class SolverAgent:
    agent_id:     str          # 'PRAGMATIC' | 'DEFENSIVE' | 'INNOVATIVE'
    system_prompt: str
    solution:     str = ""     # raw output from LLM
    revised_solution: str = "" # output after Critic feedback

@dataclass
class DebateSession:
    task_id:      str
    task_desc:    str
    solvers:      List[SolverAgent]
    critic_output: str
    judge_scores: Dict[str, Dict[str, int]]  # agent_id -> criterion -> score
    judge_justifications: Dict[str, str]
    winner_id:    str
    final_solution: str
    duration_ms:  int

class Cortex(SubsystemBase):
    def __init__(self, subsystem_id: str, message_bus: MessageBus):
        super().__init__(subsystem_id, message_bus)
        self.prompts = {
            "PRAGMATIC": "You are a Pragmatic Solver. Optimize for simplicity and runtime speed.",
            "DEFENSIVE": "You are a Defensive Solver. Optimize for correctness, edge-case coverage, and security.",
            "INNOVATIVE": "You are an Innovative Solver. Optimize for novel approaches that deviate from conventional solutions.",
            "CRITIC": "Identify the WEAKEST point in each of the three solutions provided. Do not rank them.",
            "JUDGE": "Score each solution (0-10) on Correctness, Performance, Security, and Maintainability. Format as JSON: {'agent_id': {'Correctness': N, 'Performance': N, 'Security': N, 'Maintainability': N, 'Justification': '...'}}"
        }

    async def initialize(self):
        self.logger.info("Cortex initialized.")

    async def process_message(self, envelope: MessageEnvelope):
        if envelope.msg_type == "SOLVE_COMPLEX_TASK":
            await self.run_debate(envelope)

    async def run_debate(self, envelope: MessageEnvelope):
        start_time = time.perf_counter()
        task_id = envelope.payload.get("task_id")
        task_desc = envelope.payload.get("description")

        # 1. Spawn THREE independent Solver Agents.
        solvers = [
            SolverAgent("PRAGMATIC", self.prompts["PRAGMATIC"]),
            SolverAgent("DEFENSIVE", self.prompts["DEFENSIVE"]),
            SolverAgent("INNOVATIVE", self.prompts["INNOVATIVE"])
        ]

        # 2. Each Solver produces a complete solution independently.
        solve_tasks = [self._call_llm(s.system_prompt, task_desc) for s in solvers]
        raw_results = await asyncio.gather(*solve_tasks)
        for i, res in enumerate(raw_results):
            solvers[i].solution = res

        # 3. Spawn a single Critic Agent.
        critic_input = "\n\n".join([f"Agent {s.agent_id} Solution:\n{s.solution}" for s in solvers])
        critic_output = await self._call_llm(self.prompts["CRITIC"], critic_input)

        # 4. Each Solver receives Critic's analysis and produces a revised solution.
        revision_tasks = []
        for s in solvers:
            rev_prompt = f"Original task: {task_desc}\n\nCritic analysis of your solution: {critic_output}\n\nProduce a revised solution."
            revision_tasks.append(self._call_llm(s.system_prompt, rev_prompt))

        revised_results = await asyncio.gather(*revision_tasks)
        for i, res in enumerate(revised_results):
            solvers[i].revised_solution = res

        # 5. Spawn a single Judge Agent.
        judge_input = "\n\n".join([f"Agent {s.agent_id} Revised Solution:\n{s.revised_solution}" for s in solvers])
        judge_input += f"\n\nOriginal Critic Analysis:\n{critic_output}"
        judge_output = await self._call_llm(self.prompts["JUDGE"], judge_input)

        scores, justifications, winner_id = self._parse_judge_output(judge_output, solvers)

        end_time = time.perf_counter()
        session = DebateSession(
            task_id=task_id,
            task_desc=task_desc,
            solvers=solvers,
            critic_output=critic_output,
            judge_scores=scores,
            judge_justifications=justifications,
            winner_id=winner_id,
            final_solution=next(s.revised_solution for s in solvers if s.agent_id == winner_id),
            duration_ms=int((end_time - start_time) * 1000)
        )

        # 6. Selected solution is delivered.
        await self.message_bus.send(MessageEnvelope(
            str(uuid.uuid4()), self.subsystem_id, envelope.sender_id, "DEBATE_COMPLETE",
            {"session": session.__dict__}, time.time(), envelope.priority, envelope.msg_id
        ))

        # 7. Full debate transcript stored in MEMORY-GRAPH.
        await self.message_bus.send(MessageEnvelope(
            str(uuid.uuid4()), self.subsystem_id, "SYS-02", "STORE_DATA",
            {"table": "decisions", "data": {
                "decision_id": str(uuid.uuid4()),
                "task_id": task_id,
                "timestamp": time.time(),
                "description": f"Debate for task {task_id}",
                "rationale": json.dumps(session.judge_justifications),
                "files_affected": "[]"
            }}, time.time(), 5, envelope.msg_id
        ))

    async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        msg_id = str(uuid.uuid4())
        await self.message_bus.send(MessageEnvelope(
            msg_id, self.subsystem_id, "SYS-06", "LLM_CALL",
            {"model": "gpt-4o", "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]}, time.time(), 1, msg_id
        ))
        res = await self.message_bus.receive(self.subsystem_id, timeout=60.0)
        if res and res.payload.get("status") == "success":
            return res.payload["response"]["choices"][0]["message"]["content"]
        return "Error calling LLM."

    def _parse_judge_output(self, output: str, solvers: List[SolverAgent]) -> tuple:
        try:
            # Extract JSON from LLM output
            match = re.search(r'\{.*\}', output, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                scores = {}
                justifications = {}
                max_score = -1
                winner = "DEFENSIVE"

                for s in solvers:
                    s_data = data.get(s.agent_id, {})
                    s_scores = {k: int(s_data.get(k, 0)) for k in ["Correctness", "Performance", "Security", "Maintainability"]}
                    scores[s.agent_id] = s_scores
                    justifications[s.agent_id] = s_data.get("Justification", "No justification provided.")

                    total = sum(s_scores.values())
                    if total > max_score:
                        max_score = total
                        winner = s.agent_id
                    elif total == max_score and s.agent_id == "DEFENSIVE":
                        winner = "DEFENSIVE"

                return scores, justifications, winner
        except Exception as e:
            self.logger.error(f"Failed to parse judge output: {e}")

        # Fallback to defensive tie-break if parsing fails
        return {s.agent_id: {} for s in solvers}, {s.agent_id: "Parsing failed." for s in solvers}, "DEFENSIVE"
