import pytest
from unittest.mock import AsyncMock, patch
from subsystems.omnirouter import OmniRouter, TokenOptimizer
from core.message_bus import MessageBus, MessageEnvelope
import uuid
import time

@pytest.mark.asyncio
async def test_omnirouter_llm_call_mock():
    bus = MessageBus()
    router = OmniRouter("SYS-06", bus)

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_complete:
        mock_complete.return_value = {"choices": [{"message": {"content": "mocked response"}}]}

        payload = {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "test"}]
        }

        result = await router.call_llm(payload)
        assert result["status"] == "success"
        assert result["response"]["choices"][0]["message"]["content"] == "mocked response"

@pytest.mark.asyncio
async def test_token_optimizer_duplicates():
    opt = TokenOptimizer()
    messages = [
        {"role": "user", "content": "hello"},
        {"role": "user", "content": "hello"},
        {"role": "user", "content": "world"}
    ]
    optimized = opt.optimize(messages, 4096)
    assert len(optimized) == 2
    assert optimized[0]["content"] == "hello"
    assert optimized[1]["content"] == "world"

@pytest.mark.asyncio
async def test_token_optimizer_history():
    opt = TokenOptimizer()
    messages = [{"role": "user", "content": str(i)} for i in range(15)]
    optimized = opt.optimize(messages, 4096)
    # 10 history + 1 summary notice
    assert len(optimized) == 11
    assert optimized[1]["content"] == "5"

@pytest.mark.asyncio
async def test_omnirouter_message_processing():
    bus = MessageBus()
    router = OmniRouter("SYS-06", bus)
    bus.register_subsystem("SYS-01")

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_complete:
        mock_complete.return_value = {"choices": [{"message": {"content": "processed"}}]}

        env = MessageEnvelope(
            msg_id="M1",
            sender_id="SYS-01",
            receiver_id="SYS-06",
            msg_type="LLM_CALL",
            payload={"model": "claude-3-sonnet", "messages": []},
            timestamp=0,
            priority=3,
            correlation_id="C1"
        )

        await bus.send(env)
        # In a real scenario we'd run router.run(), but here we test process_message directly
        await router.process_message(env)

        response = await bus.receive("SYS-01")
        assert response.msg_type == "LLM_RESPONSE"
        assert response.payload["status"] == "success"

@pytest.mark.asyncio
async def test_omnirouter_error_handling():
    bus = MessageBus()
    router = OmniRouter("SYS-06", bus)

    with patch("litellm.acompletion", side_effect=Exception("API Error")):
        result = await router.call_llm({"model": "error-model", "messages": []})
        assert result["status"] == "error"
        assert result["message"] == "API Error"
