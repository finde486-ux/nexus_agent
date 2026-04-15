import asyncio
import litellm
import uuid
import time
from typing import List, Dict, Any, Optional
from core.subsystem_base import SubsystemBase
from core.message_bus import MessageBus, MessageEnvelope

class TokenOptimizer:
    def __init__(self):
        self.history_limit = 10

    def optimize(self, messages: List[Dict[str, str]], context_limit: int) -> List[Dict[str, str]]:
        # 1. Remove duplicate content
        messages = self._remove_duplicates(messages)

        # 2. Summarize conversation history > 10 turns
        if len(messages) > self.history_limit:
            messages = self._summarize_history(messages)

        # 3. Replace large code blocks not directly relevant
        messages = self._summarize_large_blocks(messages)

        # 4. Semantic chunking (Phase 3 will integrate ChromaDB)
        return messages

    def _remove_duplicates(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        seen = set()
        unique_messages = []
        for msg in messages:
            content = msg.get("content", "")
            if content not in seen:
                unique_messages.append(msg)
                seen.add(content)
        return unique_messages

    def _summarize_history(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        # Section 3.6.2: Summarize old history into a compact summary paragraph.
        # For Phase 2, we simulate this by keeping the last 10 and prepending a notice.
        summary_notice = {"role": "system", "content": "Summary of previous turns: [System-generated summary]"}
        return [summary_notice] + messages[-self.history_limit:]

    def _summarize_large_blocks(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        # Phase 2 implementation of large block replacement.
        new_messages = []
        for msg in messages:
            content = msg.get("content", "")
            if len(content) > 2000: # Threshold for 'large'
                new_messages.append({"role": msg["role"], "content": content[:500] + "... [Block summarized]"})
            else:
                new_messages.append(msg)
        return new_messages

class OmniRouter(SubsystemBase):
    def __init__(self, subsystem_id: str, message_bus: MessageBus):
        super().__init__(subsystem_id, message_bus)
        self.optimizer = TokenOptimizer()

    async def initialize(self):
        self.logger.info("OmniRouter initialized.")

    async def process_message(self, envelope: MessageEnvelope):
        if envelope.msg_type == "LLM_CALL":
            result = await self.call_llm(envelope.payload)
            response = MessageEnvelope(
                msg_id=str(uuid.uuid4()),
                sender_id=self.subsystem_id,
                receiver_id=envelope.sender_id,
                msg_type="LLM_RESPONSE",
                payload=result,
                timestamp=time.time(),
                priority=envelope.priority,
                correlation_id=envelope.msg_id
            )
            await self.message_bus.send(response)

    async def call_llm(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        model = payload.get("model")
        messages = payload.get("messages", [])
        context_limit = payload.get("context_limit", 4096)

        optimized_messages = self.optimizer.optimize(messages, context_limit)

        try:
            response = await litellm.acompletion(
                model=model,
                messages=optimized_messages,
                **payload.get("kwargs", {})
            )
            return {"status": "success", "response": response}
        except Exception as e:
            self.logger.error(f"LLM call failed: {e}")
            return {"status": "error", "message": str(e)}
