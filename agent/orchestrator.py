"""
RutinitasKu - Agent Orchestrator
Main agent loop: plan → execute → respond.
"""

import json
import logging
import time
import uuid
from datetime import datetime
from typing import AsyncGenerator, Optional

from .llm import LLMLayer
from .memory import MemoryManager
from .prompt import get_system_prompt, get_reminder_prompt

from tools.registry import registry

# Import all tools to register them
import tools.web_search
import tools.web_scrape
import tools.file_manager
import tools.csv_analyzer
import tools.email_tool
import tools.calendar_tool
import tools.reminder

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Main agent orchestrator that handles:
    - Conversation management
    - Tool execution
    - Reminder checking
    - LLM interaction with fallback
    """

    def __init__(self):
        self.llm = LLMLayer()
        self.memory = MemoryManager()
        self.current_session_id = None

    async def initialize(self):
        """Initialize the orchestrator and its components."""
        await self.memory.initialize()
        logger.info("Agent orchestrator initialized")

    async def close(self):
        """Cleanup resources."""
        await self.memory.close()

    def create_session(self) -> str:
        """Create a new conversation session."""
        session_id = str(uuid.uuid4())
        self.current_session_id = session_id
        logger.info(f"Created new session: {session_id}")
        return session_id

    def set_session(self, session_id: str):
        """Set the current session."""
        self.current_session_id = session_id

    async def chat(
        self,
        user_message: str,
        session_id: str = None
    ) -> str:
        """
        Process a user message and return response.

        Args:
            user_message: User's message
            session_id: Optional session ID (uses current if not provided)

        Returns:
            Agent's response
        """
        session_id = session_id or self.current_session_id
        if not session_id:
            session_id = self.create_session()

        start_time = time.time()

        try:
            # Save user message
            await self.memory.add_message(session_id, "user", user_message)

            # Check for pending reminders
            reminder_context = await self._check_reminders()

            # Get user facts for personalization
            facts = await self.memory.get_all_facts()

            # Build system prompt
            system_prompt = get_system_prompt(facts)
            if reminder_context:
                system_prompt += "\n\n" + reminder_context

            # Get conversation history
            messages = await self.memory.get_messages_for_llm(session_id, limit=20)

            # Get tool definitions
            tools = registry.get_tool_definitions()

            # Agent loop - handle tool calls
            response_content = ""
            max_iterations = 5  # Prevent infinite loops

            for iteration in range(max_iterations):
                # Call LLM
                response = await self.llm.chat(
                    messages=messages,
                    tools=tools,
                    system=system_prompt
                )

                response_content = response.content

                # If no tool calls, we're done
                if not response.tool_calls:
                    break

                # Execute tool calls
                tool_results = []
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["arguments"]
                    tool_call_id = tool_call["id"]

                    logger.info(f"Executing tool: {tool_name}")

                    try:
                        # Handle special tool responses
                        result = await self._execute_tool(tool_name, tool_args, session_id)
                        tool_results.append({
                            "tool_call_id": tool_call_id,
                            "content": str(result)
                        })
                    except Exception as e:
                        logger.error(f"Tool execution failed: {e}")
                        tool_results.append({
                            "tool_call_id": tool_call_id,
                            "content": f"Error: {str(e)}"
                        })

                # Add assistant message with tool calls to conversation
                await self.memory.add_message(
                    session_id,
                    "assistant",
                    response_content,
                    tool_calls=response.tool_calls
                )

                # Add tool results to conversation
                for result in tool_results:
                    await self.memory.add_message(
                        session_id,
                        "tool",
                        result["content"]
                    )

                # Update messages for next iteration
                messages = await self.memory.get_messages_for_llm(session_id, limit=20)

                # Add tool results to messages for LLM
                for result in tool_results:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": result["tool_call_id"],
                        "content": result["content"]
                    })

            # Save assistant response
            await self.memory.add_message(session_id, "assistant", response_content)

            # Log task execution
            duration_ms = int((time.time() - start_time) * 1000)
            await self.memory.log_task(
                session_id=session_id,
                tool_name="chat",
                input_params={"message": user_message[:500]},
                output_result={"response_length": len(response_content)},
                status="success",
                duration_ms=duration_ms
            )

            return response_content

        except Exception as e:
            logger.error(f"Chat error: {e}")

            # Log failed task
            duration_ms = int((time.time() - start_time) * 1000)
            await self.memory.log_task(
                session_id=session_id,
                tool_name="chat",
                input_params={"message": user_message[:500]},
                output_result={"error": str(e)},
                status="error",
                duration_ms=duration_ms
            )

            return f"Maaf, terjadi error: {str(e)}"

    async def chat_stream(
        self,
        user_message: str,
        session_id: str = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat response.

        Args:
            user_message: User's message
            session_id: Optional session ID

        Yields:
            Response chunks
        """
        session_id = session_id or self.current_session_id
        if not session_id:
            session_id = self.create_session()

        try:
            # Save user message
            await self.memory.add_message(session_id, "user", user_message)

            # Check reminders
            reminder_context = await self._check_reminders()

            # Get facts and build prompt
            facts = await self.memory.get_all_facts()
            system_prompt = get_system_prompt(facts)
            if reminder_context:
                system_prompt += "\n\n" + reminder_context

            # Get conversation history
            messages = await self.memory.get_messages_for_llm(session_id, limit=20)

            # Get tools
            tools = registry.get_tool_definitions()

            # Stream response
            full_response = ""
            async for chunk in self.llm.chat_stream(messages, tools, system_prompt):
                full_response += chunk
                yield chunk

            # Save response
            await self.memory.add_message(session_id, "assistant", full_response)

        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"\n\nError: {str(e)}"

    async def _execute_tool(
        self,
        tool_name: str,
        arguments: dict,
        session_id: str
    ) -> str:
        """
        Execute a tool with special handling for certain tools.

        Args:
            tool_name: Tool name
            arguments: Tool arguments
            session_id: Current session ID

        Returns:
            Tool execution result
        """
        # Handle reminder set - need to store in memory
        if tool_name == "set_reminder":
            result = await registry.execute(tool_name, arguments)

            # Parse reminder details from result
            if result.startswith("REMINDER_SET|"):
                parts = result.split("|", 2)
                if len(parts) == 3:
                    trigger_at = datetime.fromisoformat(parts[1])
                    message = parts[2].split("\n")[0]  # Get just the message part
                    await self.memory.add_reminder(message, trigger_at)

            return result

        # Handle list reminders
        elif tool_name == "list_reminders":
            reminders = await self.memory.get_active_reminders()
            if not reminders:
                return "Tidak ada reminder aktif"

            result = "📋 Reminder Aktif:\n\n"
            for r in reminders:
                result += f"ID: {r['id']} | {r['message']}\n"
                result += f"   Jadwal: {r['trigger_at']}\n\n"
            return result

        # Handle delete reminder
        elif tool_name == "delete_reminder":
            reminder_id = arguments.get("reminder_id")
            await self.memory.delete_reminder(reminder_id)
            return f"Reminder ID {reminder_id} berhasil dihapus"

        # Handle fact saving
        elif tool_name == "save_fact":
            key = arguments.get("key")
            value = arguments.get("value")
            await self.memory.save_fact(key, value)
            return f"Fakta tersimpan: {key} = {value}"

        # Default tool execution
        else:
            return await registry.execute(tool_name, arguments)

    async def _check_reminders(self) -> Optional[str]:
        """
        Check for pending reminders and return context.

        Returns:
            Reminder context string or None
        """
        reminders = await self.memory.get_pending_reminders()

        if not reminders:
            return None

        # Mark reminders as triggered
        for reminder in reminders:
            await self.memory.mark_reminder_triggered(reminder["id"])

        # Build reminder context
        return get_reminder_prompt(reminders)

    async def get_sessions(self) -> list[dict]:
        """Get list of all sessions."""
        return await self.memory.get_sessions()

    async def clear_session(self, session_id: str):
        """Clear a session's history."""
        await self.memory.clear_session(session_id)

    async def get_task_stats(self, session_id: str = None) -> dict:
        """Get task execution statistics."""
        return await self.memory.get_task_stats(session_id)

    async def save_user_preference(self, key: str, value: str):
        """Save a user preference/fact."""
        await self.memory.save_fact(key, value)