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
from .planner import planner

from tools.registry import registry
from config import rate_limiter

# Import all tools to register them
import tools.web_search
import tools.web_scrape
import tools.file_manager
import tools.csv_analyzer
import tools.email_tool
import tools.calendar_tool
import tools.reminder
import tools.pdf_reader
import tools.planner_tool

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
        await self.llm.close()

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
            # Rate limiting check
            if not rate_limiter.is_allowed():
                wait_time = rate_limiter.get_wait_time()
                return f"Maaf, Anda terlalu banyak request. Silakan tunggu {wait_time:.0f} detik."

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

            # Inject active plan context
            plan_context = planner.get_plan_context(session_id)
            if plan_context:
                system_prompt += f"\n\n{plan_context}"

            # Get conversation history
            messages = await self.memory.get_messages_for_llm(session_id, limit=20)

            # Summarize if conversation is getting long
            if len(messages) > 15:
                messages = await self._summarize_if_needed(session_id, messages)

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

                # Persist the assistant turn that requested the tools
                await self.memory.add_message(
                    session_id,
                    "assistant",
                    response_content,
                    tool_calls=response.tool_calls
                )

                # Persist every tool result as a single turn
                await self.memory.add_message(
                    session_id,
                    "tool",
                    "",
                    tool_results=tool_results
                )

                # Continue the conversation in Anthropic-native format so the
                # model can see the tool output on the next iteration.
                messages.append(
                    self._build_assistant_tool_message(response_content, response.tool_calls)
                )
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": result["tool_call_id"],
                            "content": result["content"],
                        }
                        for result in tool_results
                    ],
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
        Stream chat response, executing tools when the model asks for them.

        Text is yielded token-by-token. When the model requests a tool, the
        tool runs, its result is fed back to the model, and generation resumes
        until the model produces a final answer (or the iteration cap is hit).

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
            # Rate limiting check
            if not rate_limiter.is_allowed():
                wait_time = rate_limiter.get_wait_time()
                yield f"Maaf, Anda terlalu banyak request. Silakan tunggu {wait_time:.0f} detik."
                return

            # Save user message
            await self.memory.add_message(session_id, "user", user_message)

            # Check reminders
            reminder_context = await self._check_reminders()

            # Get facts and build prompt
            facts = await self.memory.get_all_facts()
            system_prompt = get_system_prompt(facts)
            if reminder_context:
                system_prompt += "\n\n" + reminder_context

            # Inject active plan context
            plan_context = planner.get_plan_context(session_id)
            if plan_context:
                system_prompt += f"\n\n{plan_context}"

            # Get conversation history and tools
            messages = await self.memory.get_messages_for_llm(session_id, limit=20)
            if len(messages) > 15:
                messages = await self._summarize_if_needed(session_id, messages)

            tools = registry.get_tool_definitions()

            # Agent loop - keep going while the model requests tools
            max_iterations = 5
            for _ in range(max_iterations):
                turn_text = ""
                tool_calls = []

                async for event in self.llm.chat_stream(messages, tools, system_prompt):
                    if event["type"] == "text":
                        turn_text += event["text"]
                        yield event["text"]
                    elif event["type"] == "tool_calls":
                        tool_calls = event["tool_calls"]

                # No tools requested: this was the final answer.
                if not tool_calls:
                    if turn_text:
                        await self.memory.add_message(session_id, "assistant", turn_text)
                    break

                # Persist and replay the assistant turn that requested tools.
                await self.memory.add_message(
                    session_id,
                    "assistant",
                    turn_text,
                    tool_calls=tool_calls
                )
                messages.append(self._build_assistant_tool_message(turn_text, tool_calls))

                # Execute every requested tool and collect the results.
                tool_results = []
                for tool_call in tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call.get("arguments") or {}
                    tool_call_id = tool_call["id"]

                    logger.info(f"Executing tool (stream): {tool_name}")
                    yield f"\n\n🔧 _{tool_name}_\n\n"

                    try:
                        result = await self._execute_tool(tool_name, tool_args, session_id)
                    except Exception as e:
                        logger.error(f"Tool execution failed: {e}")
                        result = f"Error: {str(e)}"

                    tool_results.append({
                        "tool_call_id": tool_call_id,
                        "content": str(result)
                    })

                await self.memory.add_message(
                    session_id,
                    "tool",
                    "",
                    tool_results=tool_results
                )
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": result["tool_call_id"],
                            "content": result["content"],
                        }
                        for result in tool_results
                    ],
                })

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

        # Handle planner tools
        elif tool_name == "create_plan":
            goal = arguments.get("goal", "")
            steps = arguments.get("steps", [])
            plan = planner.create_plan(session_id, goal, steps)
            return f"Rencana dibuat: {goal}\n{plan.to_context()}"

        elif tool_name == "update_plan_step":
            step_id = arguments.get("step_id")
            status = arguments.get("status")
            result = arguments.get("result")

            if status == "done":
                planner.mark_step_done(session_id, step_id, result)
            elif status == "failed":
                planner.mark_step_failed(session_id, step_id, result)
            elif status == "in_progress":
                planner.mark_step_in_progress(session_id, step_id)

            plan = planner.get_plan(session_id)
            if plan:
                return f"Langkah {step_id} diupdate ke {status}\n{plan.to_context()}"
            return f"Langkah {step_id} diupdate ke {status}"

        elif tool_name == "get_plan":
            plan = planner.get_plan(session_id)
            if plan:
                return plan.to_context()
            return "Tidak ada rencana aktif"

        # Default tool execution
        else:
            return await registry.execute(tool_name, arguments)

    @staticmethod
    def _build_assistant_tool_message(text: str, tool_calls: list[dict]) -> dict:
        """Build an Anthropic-native assistant turn carrying tool_use blocks."""
        content_blocks = []
        if text:
            content_blocks.append({"type": "text", "text": text})
        for tool_call in tool_calls:
            content_blocks.append({
                "type": "tool_use",
                "id": tool_call["id"],
                "name": tool_call["name"],
                "input": tool_call.get("arguments") or {},
            })
        return {"role": "assistant", "content": content_blocks}

    @staticmethod
    def _message_text(content) -> str:
        """Extract plain text from a message content string or block list."""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return " ".join(
                block.get("text", "") for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            )
        return ""

    async def _summarize_if_needed(
        self,
        session_id: str,
        messages: list[dict]
    ) -> list[dict]:
        """
        Summarize old messages if conversation is too long.
        Keeps the last 10 messages and summarizes the rest.

        Args:
            session_id: Current session ID
            messages: Full message list

        Returns:
            Condensed message list with summary
        """
        if len(messages) <= 15:
            return messages

        # Split into old and recent messages
        old_messages = messages[:-10]
        recent_messages = messages[-10:]

        # Build summary text from old messages
        summary_parts = []
        for msg in old_messages:
            role = msg.get("role", "unknown")
            content = self._message_text(msg.get("content", ""))
            if role in ("user", "assistant") and content:
                summary_parts.append(f"{role}: {content[:200]}")

        if not summary_parts:
            return messages

        # Create summary using LLM
        summary_prompt = (
            "Ringkas percakapan berikut dalam 2-3 kalimat dalam Bahasa Indonesia. "
            "Fokus pada topik utama dan kesimpulan penting:\n\n"
            + "\n".join(summary_parts[:20])  # Limit input
        )

        try:
            summary_response = await self.llm.chat(
                messages=[{"role": "user", "content": summary_prompt}],
                system="Kamu adalah asisten yang merangkum percakapan. Berikan ringkasan singkat dan padat."
            )
            summary_text = summary_response.content

            # Build condensed messages. The summary is injected as a user
            # turn because the Anthropic Messages API only accepts user and
            # assistant roles inside the messages array.
            condensed = [
                {
                    "role": "user",
                    "content": f"[Ringkasan percakapan sebelumnya]\n{summary_text}"
                }
            ]
            condensed.extend(recent_messages)

            logger.info(f"Conversation summarized: {len(messages)} -> {len(condensed)} messages")
            return condensed

        except Exception as e:
            logger.warning(f"Summarization failed: {e}. Using full history.")
            return messages

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