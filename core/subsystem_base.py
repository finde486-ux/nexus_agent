from abc import ABC, abstractmethod
import asyncio
import logging
from core.message_bus import MessageBus, MessageEnvelope

class SubsystemBase(ABC):
    def __init__(self, subsystem_id: str, message_bus: MessageBus):
        self.subsystem_id = subsystem_id
        self.message_bus = message_bus
        self.message_bus.register_subsystem(subsystem_id)
        self.logger = logging.getLogger(subsystem_id)
        self.is_running = False

    @abstractmethod
    async def initialize(self):
        pass

    @abstractmethod
    async def process_message(self, envelope: MessageEnvelope):
        pass

    async def run(self):
        self.is_running = True
        self.logger.info(f"Subsystem {self.subsystem_id} started.")
        while self.is_running:
            envelope = await self.message_bus.receive(self.subsystem_id)
            if envelope:
                try:
                    await self.process_message(envelope)
                except Exception as e:
                    self.logger.error(f"Error processing message: {e}")
            await asyncio.sleep(0.01) # Yield control

    def stop(self):
        self.is_running = False
