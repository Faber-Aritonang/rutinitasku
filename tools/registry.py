"""
NaraTask AI - Tool Registry
Decorator-based tool registration and management.
"""

import json
import logging
from typing import Callable, Any
from functools import wraps

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Registry for managing agent tools.
    Uses decorators for easy tool registration.
    """

    def __init__(self):
        self._tools: dict[str, dict] = {}
        self._functions: dict[str, Callable] = {}

    def tool(
        self,
        name: str,
        description: str,
        input_schema: dict = None
    ):
        """
        Decorator to register a tool.

        Usage:
            @registry.tool(
                name="web_search",
                description="Search the web",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"}
                    },
                    "required": ["query"]
                }
            )
            async def web_search(query: str) -> str:
                ...
        """
        def decorator(func: Callable):
            self._tools[name] = {
                "name": name,
                "description": description,
                "input_schema": input_schema or {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
            self._functions[name] = func

            @wraps(func)
            async def wrapper(*args, **kwargs):
                return await func(*args, **kwargs)

            return wrapper
        return decorator

    def get_tool_definitions(self) -> list[dict]:
        """Get all tool definitions in Anthropic format."""
        return [
            {
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["input_schema"]
            }
            for tool in self._tools.values()
        ]

    def get_openai_tool_definitions(self) -> list[dict]:
        """Get all tool definitions in OpenAI format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"]
                }
            }
            for tool in self._tools.values()
        ]

    async def execute(self, tool_name: str, arguments: dict) -> Any:
        """
        Execute a tool by name.

        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments to pass to the tool

        Returns:
            Tool execution result
        """
        if tool_name not in self._functions:
            raise ValueError(f"Tool '{tool_name}' not found")

        func = self._functions[tool_name]

        try:
            logger.info(f"Executing tool: {tool_name} with args: {arguments}")
            result = await func(**arguments)
            logger.info(f"Tool {tool_name} completed successfully")
            return result
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            raise

    def has_tool(self, tool_name: str) -> bool:
        """Check if a tool exists."""
        return tool_name in self._functions

    def list_tools(self) -> list[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    def get_tool_info(self, tool_name: str) -> dict:
        """Get information about a specific tool."""
        if tool_name not in self._tools:
            raise ValueError(f"Tool '{tool_name}' not found")
        return self._tools[tool_name]


# Global registry instance
registry = ToolRegistry()