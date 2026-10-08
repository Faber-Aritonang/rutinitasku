"""
Tests for Memory Manager
"""

import pytest
import asyncio
from datetime import datetime, timedelta

from agent.memory import MemoryManager


@pytest.fixture
async def memory():
    """Create in-memory database for testing."""
    mem = MemoryManager(db_path=":memory:")
    await mem.initialize()
    yield mem
    await mem.close()


@pytest.mark.asyncio
async def test_add_and_get_messages(memory):
    """Test adding and retrieving messages."""
    session_id = "test-session-1"

    await memory.add_message(session_id, "user", "Hello")
    await memory.add_message(session_id, "assistant", "Hi there!")

    messages = await memory.get_messages(session_id)

    assert len(messages) == 2
    # Messages are returned in chronological order (ASC)
    roles = [m["role"] for m in messages]
    assert "user" in roles
    assert "assistant" in roles


@pytest.mark.asyncio
async def test_save_and_get_fact(memory):
    """Test saving and retrieving facts."""
    await memory.save_fact("name", "Jimmy")
    await memory.save_fact("language", "Indonesian")

    name = await memory.get_fact("name")
    assert name == "Jimmy"

    facts = await memory.get_all_facts()
    assert len(facts) == 2
    assert facts["name"] == "Jimmy"


@pytest.mark.asyncio
async def test_update_fact(memory):
    """Test updating an existing fact."""
    await memory.save_fact("preference", "dark mode")
    await memory.save_fact("preference", "light mode")

    value = await memory.get_fact("preference")
    assert value == "light mode"


@pytest.mark.asyncio
async def test_reminders(memory):
    """Test reminder operations."""
    # Add reminder
    trigger_at = datetime.now() + timedelta(hours=1)
    reminder_id = await memory.add_reminder("Test reminder", trigger_at)

    # Get active reminders
    reminders = await memory.get_active_reminders()
    assert len(reminders) == 1
    assert reminders[0]["message"] == "Test reminder"

    # Mark as triggered
    await memory.mark_reminder_triggered(reminder_id)

    # Should not appear in active
    reminders = await memory.get_active_reminders()
    assert len(reminders) == 0


@pytest.mark.asyncio
async def test_clear_session(memory):
    """Test clearing session messages."""
    session_id = "test-session-clear"

    await memory.add_message(session_id, "user", "Message 1")
    await memory.add_message(session_id, "assistant", "Response 1")

    await memory.clear_session(session_id)

    messages = await memory.get_messages(session_id)
    assert len(messages) == 0