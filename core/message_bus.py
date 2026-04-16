import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Union

@dataclass
class MessageEnvelope:
    msg_id: str        # UUID v4, unique per message
    sender_id: str     # subsystem ID (e.g. 'SYS-01')
    receiver_id: str   # subsystem ID or 'BROADCAST'
    msg_type: str      # e.g. 'TASK_REQUEST', 'RESULT', 'ERROR'
    payload: dict      # arbitrary typed data
    timestamp: float   # unix epoch, from time.monotonic()
    priority: int      # 1 (highest) to 5 (lowest)
    correlation_id: str # links request/response pairs (same UUID)

class MessageBus:
    def __init__(self):
        self.inboxes: Dict[str, asyncio.Queue] = {}
        self.subscribers: Dict[str, List[str]] = {} # For BROADCAST if needed

    def register_subsystem(self, subsystem_id: str):
        if subsystem_id not in self.inboxes:
            self.inboxes[subsystem_id] = asyncio.Queue()

    async def send(self, envelope: MessageEnvelope):
        if envelope.receiver_id == 'BROADCAST':
            for subsystem_id, queue in self.inboxes.items():
                if subsystem_id != envelope.sender_id:
                    await queue.put(envelope)
        elif envelope.receiver_id in self.inboxes:
            await self.inboxes[envelope.receiver_id].put(envelope)
        else:
            # Notify error for unknown receiver
            self.inboxes.get("LOG", asyncio.Queue()).put_nowait(f"Unknown receiver: {envelope.receiver_id}")

    async def receive(self, subsystem_id: str, timeout: float = 30.0) -> Optional[MessageEnvelope]:
        if subsystem_id not in self.inboxes:
            return None

        try:
            return await asyncio.wait_for(self.inboxes[subsystem_id].get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None
