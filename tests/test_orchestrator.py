"""
Tests for Agent Orchestrator
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from agent.orchestrator import AgentOrchestrator
from agent.llm import LLMResponse


@pytest.fixture
async def orchestrator():
    """Create orchestrator with mocked dependencies."""
    with patch("agent.orchestrator.LLMLayer") as MockLLM, \
         patch("agent.orchestrator.MemoryManager") as MockMemory:

        # Setup mock memory
        mock_memory = AsyncMock()
        MockMemory.return_value = mock_memory
        mock_memory.get_messages_for_llm.return_value = []
        mock_memory.get_pending_reminders.return_value = []
        mock_memory.get_all_facts.return_value = {}
        mock_memory.get_active_reminders.return_value = []

        # Setup mock LLM
        mock_llm = AsyncMock()
        MockLLM.return_value = mock_llm

        orch = AgentOrchestrator()
        orch.memory = mock_memory
        orch.llm = mock_llm

        yield orch, mock_memory, mock_llm


@pytest.mark.asyncio
async def test_create_session(orchestrator):
    """Test session creation."""
    orch, _, _ = orchestrator
    session_id = orch.create_session()

    assert session_id is not None
    assert orch.current_session_id == session_id


@pytest.mark.asyncio
async def test_chat_basic_response(orchestrator):
    """Test basic chat without tool calls."""
    orch, mock_memory, mock_llm = orchestrator

    # Setup LLM response
    mock_llm.chat.return_value = LLMResponse(
        content="Halo! Ada yang bisa saya bantu?",
        tool_calls=[],
        usage={"input_tokens": 10, "output_tokens": 20},
        provider="anthropic",
        model="claude-sonnet-4-20250514"
    )

    response = await orch.chat("Halo", session_id="test-session")

    assert "Halo" in response
    mock_memory.add_message.assert_called()


@pytest.mark.asyncio
async def test_chat_with_tool_call(orchestrator):
    """Test chat with tool execution."""
    orch, mock_memory, mock_llm = orchestrator

    # First response has a tool call
    tool_response = LLMResponse(
        content="Saya akan mencari informasi...",
        tool_calls=[{
            "id": "call_1",
            "name": "web_search",
            "arguments": {"query": "test query"}
        }],
        usage={"input_tokens": 10, "output_tokens": 20},
        provider="anthropic",
        model="claude-sonnet-4-20250514"
    )

    # Second response is final
    final_response = LLMResponse(
        content="Berikut hasil pencarian...",
        tool_calls=[],
        usage={"input_tokens": 10, "output_tokens": 20},
        provider="anthropic",
        model="claude-sonnet-4-20250514"
    )

    mock_llm.chat.side_effect = [tool_response, final_response]

    # Mock tool execution
    with patch("agent.orchestrator.registry") as mock_registry:
        mock_registry.get_tool_definitions.return_value = []
        mock_registry.execute.return_value = "Search results"

        # Need to handle the orchestrator's _execute_tool
        response = await orch.chat("Cari info tentang AI", session_id="test-session")

    assert response is not None


@pytest.mark.asyncio
async def test_chat_handles_error(orchestrator):
    """Test error handling in chat."""
    orch, mock_memory, mock_llm = orchestrator

    mock_llm.chat.side_effect = Exception("API Error")

    response = await orch.chat("Test", session_id="test-session")

    assert "error" in response.lower()


@pytest.mark.asyncio
async def test_check_reminders(orchestrator):
    """Test reminder checking."""
    orch, mock_memory, _ = orchestrator

    mock_memory.get_pending_reminders.return_value = [
        {"id": 1, "message": "Meeting jam 2", "trigger_at": "2024-01-01T14:00:00"}
    ]

    result = await orch._check_reminders()

    assert result is not None
    assert "Meeting" in result
    mock_memory.mark_reminder_triggered.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_check_no_reminders(orchestrator):
    """Test when no pending reminders."""
    orch, mock_memory, _ = orchestrator

    mock_memory.get_pending_reminders.return_value = []

    result = await orch._check_reminders()

    assert result is None


@pytest.mark.asyncio
async def test_execute_tool_save_fact(orchestrator):
    """Test save_fact tool execution."""
    orch, mock_memory, _ = orchestrator

    result = await orch._execute_tool(
        "save_fact",
        {"key": "name", "value": "Jimmy"},
        "test-session"
    )

    assert "tersimpan" in result.lower() or "saved" in result.lower()
    mock_memory.save_fact.assert_called_once_with("name", "Jimmy")


@pytest.mark.asyncio
async def test_execute_tool_list_reminders(orchestrator):
    """Test list_reminders tool execution."""
    orch, mock_memory, _ = orchestrator

    mock_memory.get_active_reminders.return_value = [
        {"id": 1, "message": "Test reminder", "trigger_at": "2024-01-01T14:00:00"}
    ]

    result = await orch._execute_tool("list_reminders", {}, "test-session")

    assert "Test reminder" in result


@pytest.mark.asyncio
async def test_execute_tool_delete_reminder(orchestrator):
    """Test delete_reminder tool execution."""
    orch, mock_memory, _ = orchestrator

    result = await orch._execute_tool(
        "delete_reminder",
        {"reminder_id": 1},
        "test-session"
    )

    assert "berhasil" in result.lower() or "deleted" in result.lower()
    mock_memory.delete_reminder.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_get_task_stats(orchestrator):
    """Test task statistics retrieval."""
    orch, mock_memory, _ = orchestrator

    mock_memory.get_task_stats.return_value = {
        "chat": {"total": 10, "success": 9, "avg_duration_ms": 500}
    }

    stats = await orch.get_task_stats("test-session")

    assert "chat" in stats
    assert stats["chat"]["total"] == 10