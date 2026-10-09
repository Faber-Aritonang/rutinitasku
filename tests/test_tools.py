"""
Tests for Tools
"""

import pytest
from tools.registry import ToolRegistry


@pytest.fixture
def registry():
    """Create fresh registry for testing."""
    return ToolRegistry()


def test_register_tool(registry):
    """Test tool registration."""
    @registry.tool(
        name="test_tool",
        description="A test tool",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"}
            }
        }
    )
    async def test_tool(query: str) -> str:
        return f"Result: {query}"

    assert registry.has_tool("test_tool")
    assert "test_tool" in registry.list_tools()


def test_get_tool_definitions(registry):
    """Test getting tool definitions."""
    @registry.tool(
        name="tool1",
        description="Tool 1",
        input_schema={"type": "object", "properties": {}}
    )
    async def tool1() -> str:
        return "ok"

    definitions = registry.get_tool_definitions()

    assert len(definitions) == 1
    assert definitions[0]["name"] == "tool1"


@pytest.mark.asyncio
async def test_execute_tool(registry):
    """Test tool execution."""
    @registry.tool(
        name="add",
        description="Add two numbers",
        input_schema={
            "type": "object",
            "properties": {
                "a": {"type": "integer"},
                "b": {"type": "integer"}
            }
        }
    )
    async def add(a: int, b: int) -> str:
        return str(a + b)

    result = await registry.execute("add", {"a": 2, "b": 3})
    assert result == "5"


@pytest.mark.asyncio
async def test_execute_nonexistent_tool(registry):
    """Test executing non-existent tool."""
    with pytest.raises(ValueError, match="not found"):
        await registry.execute("nonexistent", {})

def test_email_search_criteria_single_day():
    """Satu hari penuh: SINCE hari itu, BEFORE hari berikutnya."""
    from tools.email_tool import _build_search_criteria

    assert _build_search_criteria(since="2026-10-08", before="2026-10-09") == (
        "SINCE 08-Oct-2026 BEFORE 09-Oct-2026"
    )


def test_email_search_criteria_defaults_and_combination():
    from tools.email_tool import _build_search_criteria

    assert _build_search_criteria() == "ALL"
    assert _build_search_criteria(unread_only=True, search="FROM john") == "UNSEEN FROM john"


def test_email_search_criteria_rejects_bad_date():
    from tools.email_tool import _build_search_criteria

    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        _build_search_criteria(since="8 Oktober")
