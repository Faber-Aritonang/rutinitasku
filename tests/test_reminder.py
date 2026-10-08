"""
Tests for Reminder Tool
"""

import pytest
from datetime import datetime, timedelta

from tools.reminder import set_reminder, list_reminders, delete_reminder, save_fact
from tools.registry import registry


def test_reminder_tools_registered():
    """Test all reminder tools are registered."""
    assert registry.has_tool("set_reminder")
    assert registry.has_tool("list_reminders")
    assert registry.has_tool("delete_reminder")
    assert registry.has_tool("save_fact")


@pytest.mark.asyncio
async def test_set_reminder_with_time():
    """Test setting reminder with specific time."""
    result = await set_reminder(
        message="Meeting jam 2",
        time="2025-12-25 14:00"
    )

    assert "REMINDER_SET" in result
    assert "Meeting jam 2" in result


@pytest.mark.asyncio
async def test_set_reminder_with_duration():
    """Test setting reminder with duration."""
    result = await set_reminder(
        message="Cek email",
        duration="30m"
    )

    assert "REMINDER_SET" in result
    assert "Cek email" in result


@pytest.mark.asyncio
async def test_set_reminder_time_only():
    """Test setting reminder with time only (HH:MM)."""
    result = await set_reminder(
        message="Sarapan",
        time="08:00"
    )

    assert "REMINDER_SET" in result
    assert "Sarapan" in result


@pytest.mark.asyncio
async def test_set_reminder_invalid_duration():
    """Test setting reminder with invalid duration."""
    result = await set_reminder(
        message="Test",
        duration="invalid"
    )

    assert "Error" in result or "error" in result.lower()


@pytest.mark.asyncio
async def test_set_reminder_no_time():
    """Test setting reminder without time or duration."""
    result = await set_reminder(message="Test")

    assert "Error" in result or "error" in result.lower()


@pytest.mark.asyncio
async def test_list_reminders():
    """Test listing reminders returns sentinel."""
    result = await list_reminders()
    assert result == "LIST_REMINDERS"


@pytest.mark.asyncio
async def test_delete_reminder():
    """Test deleting reminder returns sentinel."""
    result = await delete_reminder(reminder_id=1)
    assert "DELETE_REMINDER" in result
    assert "1" in result


@pytest.mark.asyncio
async def test_save_fact():
    """Test save_fact returns sentinel."""
    result = await save_fact(key="name", value="Jimmy")
    assert "SAVE_FACT" in result
    assert "name" in result
    assert "Jimmy" in result


def test_reminder_tool_definitions():
    """Test reminder tool definitions are properly formatted."""
    definitions = registry.get_tool_definitions()

    set_def = next((d for d in definitions if d["name"] == "set_reminder"), None)
    assert set_def is not None
    assert "message" in set_def["input_schema"]["properties"]
    assert "message" in set_def["input_schema"]["required"]

    list_def = next((d for d in definitions if d["name"] == "list_reminders"), None)
    assert list_def is not None

    delete_def = next((d for d in definitions if d["name"] == "delete_reminder"), None)
    assert delete_def is not None
    assert "reminder_id" in delete_def["input_schema"]["properties"]