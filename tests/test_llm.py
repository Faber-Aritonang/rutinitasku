"""
Tests for LLM Layer
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from agent.llm import LLMLayer, LLMResponse


@pytest.fixture
def llm_layer():
    """Create LLM layer instance for testing."""
    with patch("agent.llm.ANTHROPIC_API_KEY", "test-key"), \
         patch("agent.llm.NARAROUTER_API_KEY", "test-key"):
        layer = LLMLayer()
        return layer


def test_llm_response_dataclass():
    """Test LLMResponse dataclass."""
    response = LLMResponse(
        content="Hello",
        tool_calls=[],
        usage={"input_tokens": 10, "output_tokens": 20},
        provider="anthropic",
        model="claude-sonnet-4-20250514"
    )

    assert response.content == "Hello"
    assert response.provider == "anthropic"
    assert response.usage["input_tokens"] == 10


def test_is_available(llm_layer):
    """Test availability check."""
    status = llm_layer.is_available()
    assert "claude" in status
    assert "nararouter" in status


def test_llm_clients_disable_brotli_encoding():
    """Avoid the system Brotli decoder API mismatch in SDK requests."""
    with patch("agent.llm.ANTHROPIC_API_KEY", "test-key"), \
         patch("agent.llm.NARAROUTER_API_KEY", "test-key"):
        layer = LLMLayer()

    assert layer.claude_client._client.headers["accept-encoding"] == "gzip, deflate"
    assert layer.nararouter_client._client.headers["accept-encoding"] == "gzip, deflate"


@pytest.mark.asyncio
async def test_call_claude_does_not_send_unsupported_temperature(llm_layer):
    """Anthropic Messages API does not accept the temperature parameter."""
    mock_response = MagicMock(
        content=[],
        usage=MagicMock(input_tokens=1, output_tokens=1)
    )
    llm_layer.claude_client.messages.create = AsyncMock(return_value=mock_response)

    await llm_layer._call_claude([{"role": "user", "content": "Halo"}], None, None)

    request_kwargs = llm_layer.claude_client.messages.create.await_args.kwargs
    assert "temperature" not in request_kwargs


def test_convert_tools_to_openai(llm_layer):
    """Test tool format conversion."""
    anthropic_tools = [
        {
            "name": "test_tool",
            "description": "A test tool",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                }
            }
        }
    ]

    openai_tools = llm_layer._convert_tools_to_openai(anthropic_tools)

    assert len(openai_tools) == 1
    assert openai_tools[0]["type"] == "function"
    assert openai_tools[0]["function"]["name"] == "test_tool"