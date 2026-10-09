"""
Tests for LLM Layer
"""

import json
import pytest
import asyncio
from types import SimpleNamespace
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


def test_messages_to_openai_converts_tool_roundtrip(llm_layer):
    """Anthropic-style tool_use/tool_result blocks become OpenAI messages."""
    messages = [
        {"role": "user", "content": "Ringkas 6 email teratas"},
        {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "Saya akan membaca email."},
                {"type": "tool_use", "id": "call_1", "name": "email_read", "input": {"limit": 6}},
            ],
        },
        {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "call_1", "content": "EMAILS"},
            ],
        },
    ]

    converted = llm_layer._messages_to_openai(messages)

    assert converted[1]["role"] == "assistant"
    assert converted[1]["content"] == "Saya akan membaca email."
    assert converted[1]["tool_calls"][0]["id"] == "call_1"
    assert converted[1]["tool_calls"][0]["function"]["name"] == "email_read"
    assert json.loads(converted[1]["tool_calls"][0]["function"]["arguments"]) == {"limit": 6}
    assert converted[2] == {"role": "tool", "tool_call_id": "call_1", "content": "EMAILS"}


def _fake_chunk(content=None, tool_calls=None):
    delta = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(delta=delta)])


def _fake_tool_call_delta(index, id=None, name=None, arguments=None):
    function = SimpleNamespace(name=name, arguments=arguments)
    return SimpleNamespace(index=index, id=id, function=function)


@pytest.mark.asyncio
async def test_nararouter_stream_reassembles_tool_calls(llm_layer):
    """Fragmented streaming tool calls are rebuilt and surfaced as an event."""

    async def fake_stream():
        yield _fake_chunk(content="Ringkasan: ")
        yield _fake_chunk(tool_calls=[
            _fake_tool_call_delta(0, id="call_1", name="email_read", arguments='{"limit"')
        ])
        yield _fake_chunk(tool_calls=[
            _fake_tool_call_delta(0, arguments=': 6}')
        ])

    llm_layer.nararouter_client.chat.completions.create = AsyncMock(
        return_value=fake_stream()
    )

    events = [
        event async for event in llm_layer._stream_events_nararouter(
            [{"role": "user", "content": "Ringkas email"}], None, None
        )
    ]

    assert {"type": "text", "text": "Ringkasan: "} in events
    tool_event = next(e for e in events if e["type"] == "tool_calls")
    assert tool_event["tool_calls"] == [
        {"id": "call_1", "name": "email_read", "arguments": {"limit": 6}}
    ]