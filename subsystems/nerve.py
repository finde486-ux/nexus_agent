import psutil
import time
import uuid
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from core.subsystem_base import SubsystemBase
from core.message_bus import MessageBus, MessageEnvelope

@dataclass
class ResourceBudget:
    max_ram_bytes:    int   # hard ceiling — solution must fit within this
    max_cpu_cores:    int   # maximum parallel threads
    max_exec_ms:      int   # maximum allowed runtime in milliseconds
    max_disk_bytes:   int   # maximum disk writes
    gpu_allowed:      bool  # whether GPU execution is permitted

class Nerve(SubsystemBase):
    def __init__(self, subsystem_id: str, message_bus: MessageBus):
        super().__init__(subsystem_id, message_bus)
        self.sampling_interval = 0.5 # 500ms

    async def initialize(self):
        self.logger.info("Nerve initialized.")

    async def process_message(self, envelope: MessageEnvelope):
        if envelope.msg_type == "GET_BUDGET":
            budget = self.compute_budget()
            response = MessageEnvelope(
                msg_id=str(uuid.uuid4()),
                sender_id=self.subsystem_id,
                receiver_id=envelope.sender_id,
                msg_type="BUDGET_RESPONSE",
                payload={"budget": budget.__dict__},
                timestamp=time.time(),
                priority=envelope.priority,
                correlation_id=envelope.msg_id
            )
            await self.message_bus.send(response)

    def get_telemetry(self) -> Dict[str, Any]:
        # 3.3.1 Monitored Metrics
        telemetry = {
            "cpu_usage": psutil.cpu_percent(percpu=True),
            "ram_available": psutil.virtual_memory().available,
            "disk_io": psutil.disk_io_counters()._asdict(),
            "network_io": psutil.net_io_counters()._asdict(),
            "process_memory": psutil.Process().memory_info().rss
        }

        # CPU Temp (might not be available on all systems)
        try:
            telemetry["cpu_temp"] = psutil.sensors_temperatures()
        except Exception:
            telemetry["cpu_temp"] = {}

        return telemetry

    def compute_budget(self) -> ResourceBudget:
        # 3.3.2 Resource Budget Contract
        mem = psutil.virtual_memory()
        cpu_count = psutil.cpu_count()

        # Safe defaults: 50% of available RAM, 60% of CPU headroom
        max_ram = int(mem.available * 0.5)
        # Assuming 100% capacity is cpu_count * 100. Headroom is count * 100 - total usage.
        # Simplified: 60% of total cores
        max_cores = max(1, int(cpu_count * 0.6))

        return ResourceBudget(
            max_ram_bytes=max_ram,
            max_cpu_cores=max_cores,
            max_exec_ms=60000, # 60s default
            max_disk_bytes=100 * 1024 * 1024, # 100MB default
            gpu_allowed=False # Default to False for now
        )

    async def run_telemetry_loop(self):
        while self.is_running:
            metrics = self.get_telemetry()
            # Action Thresholds
            if any(core > 85 for core in metrics["cpu_usage"]):
                self.logger.warning("CPU usage exceeds 85%, throttling tasks.")

            if metrics["ram_available"] < 512 * 1024 * 1024:
                self.logger.error("RAM available below 512MB, refusing tasks.")

            await asyncio.sleep(self.sampling_interval)

import asyncio
