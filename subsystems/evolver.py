import asyncio
import time
import uuid
import json
import tracemalloc
import os
from typing import List, Dict, Any, Optional
from core.subsystem_base import SubsystemBase
from core.message_bus import MessageBus, MessageEnvelope
from config import Config

class Evolver(SubsystemBase):
    def __init__(self, subsystem_id: str, message_bus: MessageBus):
        super().__init__(subsystem_id, message_bus)
        self.mutation_library = [
            "Loop unrolling", "Constant folding", "Dead code elimination",
            "Inlining", "Type narrowing", "Early return", "String interning", "Generator conversion"
        ]

    async def initialize(self):
        self.logger.info("Evolver initialized.")

    async def process_message(self, envelope: MessageEnvelope):
        if envelope.msg_type == "EVOLVE_CODE":
            await self.run_evolution(envelope)

    async def run_evolution(self, envelope: MessageEnvelope):
        start_time = time.perf_counter()
        original_code = envelope.payload.get("code")
        self.logger.info("Starting evolution protocol.")

        # 1. GENERATE 10 variations
        variations = await self._generate_variations(original_code)

        generations = 5
        best_variant = {"code": original_code, "fitness": 0}

        for gen in range(generations):
            self.logger.info(f"Generation {gen+1} starting.")

            # 2. SUBMIT to ADVERSARY for verification
            survivors = await self._verify_variations(variations)
            if not survivors: break

            # 3. BENCHMARK survivors (Must occur in Docker sandbox per Rule 6)
            benchmarks = await self._benchmark_variations(survivors)

            # 4. SCORE fitness
            scored_variants = self._score_variations(benchmarks)
            scored_variants.sort(key=lambda x: x["fitness"], reverse=True)

            current_best = scored_variants[0]
            if current_best["fitness"] > best_variant["fitness"]:
                improvement = (current_best["fitness"] - best_variant["fitness"]) / (best_variant["fitness"] or 1)
                best_variant = current_best
                if improvement < 0.02 and gen > 0:
                    break

            # 5. SELECT top 3 and MUTATE
            top_3 = scored_variants[:3]
            variations = await self._mutate_top_variants(top_3)

        # 6. DELIVER winner
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        await self.message_bus.send(MessageEnvelope(
            str(uuid.uuid4()), self.subsystem_id, envelope.sender_id, "EVOLUTION_COMPLETE",
            {"winner": best_variant, "duration_ms": duration_ms},
            time.time(), envelope.priority, envelope.msg_id
        ))

    async def _generate_variations(self, code: str) -> List[str]:
        strategies = ["Original", "Iterative", "Recursive", "Vectorized", "Memory-pool", "Cache-aware", "Parallel", "Functional", "Lazy", "Lookup-table"]
        prompt = f"Generate 10 algorithmically distinct variations of the following code based on these strategies: {strategies}. Code:\n{code}"
        return await self._call_omnirouter_multi(prompt, 10)

    async def _verify_variations(self, variations: List[str]) -> List[str]:
        survivors = []
        for v in variations:
            await self.message_bus.send(MessageEnvelope(
                str(uuid.uuid4()), self.subsystem_id, "SYS-05", "ATTACK_CODE",
                {"code_files": {"variant.py": v}, "budget": {}}, time.time(), 1, str(uuid.uuid4())
            ))
            res = await self.message_bus.receive(self.subsystem_id, timeout=30)
            if res and res.payload.get("status") == "CLEARED":
                survivors.append(v)
        return survivors

    async def _benchmark_variations(self, variations: List[str]) -> List[Dict[str, Any]]:
        results = []
        import docker
        client = docker.from_env()
        workspace = "/tmp/nexus_evolver"
        os.makedirs(workspace, exist_ok=True)

        for i, v in enumerate(variations):
            filename = f"variant_{i}.py"
            with open(os.path.join(workspace, filename), "w") as f:
                f.write(v)

            try:
                # Benchmark inside sandbox per Rule 6
                start = time.perf_counter()
                container = client.containers.run(
                    image=Config.SANDBOX_IMAGE, network_mode='none', mem_limit="512m",
                    volumes={workspace: {'bind': '/workspace', 'mode': 'rw'}},
                    command=f"python3 /workspace/{filename}",
                    auto_remove=True
                )
                duration = time.perf_counter() - start
                # Real cycle and cache miss counting would use 'perf' inside container
                results.append({"code": v, "time_ms": duration * 1000, "ram_bytes": 1000000})
            except Exception as e:
                self.logger.error(f"Benchmark failed for variant {i}: {e}")
        return results

    def _score_variations(self, benchmarks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        scored = []
        for b in benchmarks:
            fitness = (1.0 / (b["time_ms"] or 1e-6)) * 0.4 + (1.0 / (b["ram_bytes"] or 1e-6)) * 0.4 + 1 * 0.2
            b["fitness"] = fitness
            scored.append(b)
        return scored

    async def _mutate_top_variants(self, top_variants: List[Dict[str, Any]]) -> List[str]:
        mutated = []
        for v in top_variants:
            mutation = self.mutation_library[int(time.time()) % len(self.mutation_library)]
            prompt = f"Apply the micro-optimization '{mutation}' to this code:\n{v['code']}"
            res = await self._call_omnirouter(prompt)
            if res: mutated.append(res)
        return mutated

    async def _call_omnirouter(self, prompt: str) -> Optional[str]:
        msg_id = str(uuid.uuid4())
        await self.message_bus.send(MessageEnvelope(
            msg_id, self.subsystem_id, "SYS-06", "LLM_CALL",
            {"model": "gpt-4o", "messages": [{"role": "user", "content": prompt}]},
            time.time(), 1, msg_id
        ))
        res = await self.message_bus.receive(self.subsystem_id, timeout=60.0)
        return res.payload["response"]["choices"][0]["message"]["content"] if res and res.payload.get("status") == "success" else None

    async def _call_omnirouter_multi(self, prompt: str, count: int) -> List[str]:
        return [await self._call_omnirouter(prompt) for _ in range(count)]
