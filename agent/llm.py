"""
RutinitasKu - LLM Layer
Dual-provider abstraction with auto-fallback:
- Primary: Anthropic Claude API
- Fallback: NaraRouter (OpenAI-compatible)
"""

import json
import logging
from typing import AsyncGenerator, Optional
from dataclasses import dataclass

import anthropic
from openai import AsyncOpenAI

from config import (
    ANTHROPIC_API_KEY,
    ANTHROPIC_MODEL,
    NARAROUTER_API_KEY,
    NARAROUTER_BASE_URL,
    NARAROUTER_MODEL,
    MAX_TOKENS,
    TEMPERATURE
)

logger = logging.getLogger(__name__)


def _create_llm_http_client():
    """Create an SDK HTTP client without advertising unsupported Brotli."""
    try:
        # Newer SDK releases use httpx2; older releases still use httpx.
        import httpx2 as http_client_library
    except ImportError:
        import httpx as http_client_library

    return http_client_library.AsyncClient(
        headers={"Accept-Encoding": "gzip, deflate"}
    )


@dataclass
class LLMResponse:
    """Response from LLM with metadata."""
    content: str
    tool_calls: list[dict]
    usage: dict
    provider: str
    model: str


class LLMLayer:
    """
    LLM abstraction layer with dual-provider support.
    Automatically falls back to NaraRouter if Claude fails.
    """

    def __init__(self):
        self.claude_client = None
        self.nararouter_client = None
        self._http_clients = []

        # Initialize Claude client
        if ANTHROPIC_API_KEY:
            http_client = _create_llm_http_client()
            self._http_clients.append(http_client)
            self.claude_client = anthropic.AsyncAnthropic(
                api_key=ANTHROPIC_API_KEY,
                http_client=http_client
            )
            logger.info(f"Claude client initialized with model: {ANTHROPIC_MODEL}")

        # Initialize NaraRouter client
        if NARAROUTER_API_KEY:
            http_client = _create_llm_http_client()
            self._http_clients.append(http_client)
            self.nararouter_client = AsyncOpenAI(
                api_key=NARAROUTER_API_KEY,
                base_url=NARAROUTER_BASE_URL,
                http_client=http_client
            )
            logger.info(f"NaraRouter client initialized with model: {NARAROUTER_MODEL}")

    async def close(self):
        """Close the HTTP clients used by configured LLM providers."""
        for http_client in self._http_clients:
            await http_client.aclose()
        self._http_clients.clear()

    async def chat(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        system: Optional[str] = None
    ) -> LLMResponse:
        """
        Send chat request with auto-fallback.

        Args:
            messages: List of message dicts with 'role' and 'content'
            tools: Optional list of tool definitions
            system: Optional system prompt

        Returns:
            LLMResponse with content and tool_calls
        """
        # Try Claude first
        if self.claude_client:
            try:
                return await self._call_claude(messages, tools, system)
            except Exception as e:
                logger.warning(f"Claude API failed: {e}. Falling back to NaraRouter.")

        # Fallback to NaraRouter
        if self.nararouter_client:
            try:
                return await self._call_nararouter(messages, tools, system)
            except Exception as e:
                logger.error(f"NaraRouter also failed: {e}")
                raise

        raise RuntimeError("No LLM provider available. Check your API keys.")

    async def chat_stream(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        system: Optional[str] = None
    ) -> AsyncGenerator[dict, None]:
        """
        Stream chat response with auto-fallback.

        Unlike :meth:`chat`, streaming must also surface tool calls so the
        orchestrator can execute them and continue the conversation.

        Yields:
            Event dicts, one of:
              {"type": "text", "text": <chunk>}
              {"type": "tool_calls", "tool_calls": [{"id", "name", "arguments"}, ...]}
        """
        # Try Claude first. Once we have streamed a partial answer we cannot
        # replay it through the fallback provider without duplicating output,
        # so only fall back when nothing has been emitted yet.
        if self.claude_client:
            emitted = False
            try:
                async for event in self._stream_events_claude(messages, tools, system):
                    emitted = True
                    yield event
                return
            except Exception as e:
                if emitted:
                    raise
                logger.warning(f"Claude streaming failed: {e}. Falling back to NaraRouter.")

        # Fallback to NaraRouter
        if self.nararouter_client:
            try:
                async for event in self._stream_events_nararouter(messages, tools, system):
                    yield event
                return
            except Exception as e:
                logger.error(f"NaraRouter streaming also failed: {e}")
                raise

        raise RuntimeError("No LLM provider available.")

    async def _call_claude(
        self,
        messages: list[dict],
        tools: Optional[list[dict]],
        system: Optional[str]
    ) -> LLMResponse:
        """Call Anthropic Claude API."""
        kwargs = {
            "model": ANTHROPIC_MODEL,
            "max_tokens": MAX_TOKENS,
            "messages": messages,
        }

        if system:
            kwargs["system"] = system

        if tools:
            kwargs["tools"] = tools

        response = await self.claude_client.messages.create(**kwargs)

        # Extract content and tool calls
        content = ""
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "arguments": block.input
                })

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens
            },
            provider="anthropic",
            model=ANTHROPIC_MODEL
        )

    async def _call_nararouter(
        self,
        messages: list[dict],
        tools: Optional[list[dict]],
        system: Optional[str]
    ) -> LLMResponse:
        """Call NaraRouter API (OpenAI-compatible)."""
        openai_messages = self._messages_to_openai(messages)
        if system:
            openai_messages.insert(0, {"role": "system", "content": system})

        kwargs = {
            "model": NARAROUTER_MODEL,
            "messages": openai_messages,
            "max_tokens": MAX_TOKENS,
            "temperature": TEMPERATURE
        }

        if tools:
            # Convert Anthropic tool format to OpenAI format
            openai_tools = self._convert_tools_to_openai(tools)
            kwargs["tools"] = openai_tools

        response = await self.nararouter_client.chat.completions.create(**kwargs)

        choice = response.choices[0]
        content = choice.message.content or ""
        tool_calls = []

        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": self._parse_tool_arguments(tc.function.arguments)
                })

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            usage={
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens
            },
            provider="nararouter",
            model=NARAROUTER_MODEL
        )

    async def _stream_events_claude(
        self,
        messages: list[dict],
        tools: Optional[list[dict]],
        system: Optional[str]
    ) -> AsyncGenerator[dict, None]:
        """Stream response events from Claude, including tool_use blocks."""
        kwargs = {
            "model": ANTHROPIC_MODEL,
            "max_tokens": MAX_TOKENS,
            "messages": messages,
        }

        if system:
            kwargs["system"] = system

        if tools:
            kwargs["tools"] = tools

        async with self.claude_client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield {"type": "text", "text": text}
            final_message = await stream.get_final_message()

        tool_calls = []
        for block in final_message.content:
            if block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "arguments": block.input or {}
                })

        if tool_calls:
            yield {"type": "tool_calls", "tool_calls": tool_calls}

    async def _stream_events_nararouter(
        self,
        messages: list[dict],
        tools: Optional[list[dict]],
        system: Optional[str]
    ) -> AsyncGenerator[dict, None]:
        """Stream response events from NaraRouter (OpenAI-compatible)."""
        openai_messages = self._messages_to_openai(messages)
        if system:
            openai_messages.insert(0, {"role": "system", "content": system})

        kwargs = {
            "model": NARAROUTER_MODEL,
            "messages": openai_messages,
            "max_tokens": MAX_TOKENS,
            "temperature": TEMPERATURE,
            "stream": True
        }

        if tools:
            kwargs["tools"] = self._convert_tools_to_openai(tools)

        stream = await self.nararouter_client.chat.completions.create(**kwargs)

        # OpenAI-style streaming sends tool calls as fragmented deltas that
        # must be reassembled per index before they can be executed.
        pending: dict[int, dict] = {}

        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta

            if getattr(delta, "content", None):
                yield {"type": "text", "text": delta.content}

            for tc in (getattr(delta, "tool_calls", None) or []):
                index = getattr(tc, "index", 0) or 0
                acc = pending.setdefault(index, {"id": None, "name": "", "arguments": ""})
                if getattr(tc, "id", None):
                    acc["id"] = tc.id
                function = getattr(tc, "function", None)
                if function:
                    if getattr(function, "name", None):
                        acc["name"] += function.name
                    if getattr(function, "arguments", None):
                        acc["arguments"] += function.arguments

        tool_calls = [
            {
                "id": pending[i]["id"] or f"call_{i}",
                "name": pending[i]["name"],
                "arguments": self._parse_tool_arguments(pending[i]["arguments"])
            }
            for i in sorted(pending)
            if pending[i]["name"]
        ]

        if tool_calls:
            yield {"type": "tool_calls", "tool_calls": tool_calls}

    @staticmethod
    def _parse_tool_arguments(raw: Optional[str]) -> dict:
        """Parse a tool-call arguments payload, tolerating empty/invalid JSON."""
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}

    @staticmethod
    def _messages_to_openai(messages: list[dict]) -> list[dict]:
        """
        Convert provider-neutral (Anthropic-style) messages to OpenAI format.

        Text messages pass through; assistant tool_use blocks become
        ``tool_calls``; user tool_result blocks become ``tool`` messages.
        """
        openai_messages = []

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")

            # Plain text message (or malformed/unknown shape)
            if isinstance(content, str) or role == "tool":
                openai_messages.append({"role": role, "content": content})
                continue

            if role == "assistant" and isinstance(content, list):
                text_parts = [b.get("text", "") for b in content if b.get("type") == "text"]
                tool_calls = [
                    {
                        "id": b.get("id"),
                        "type": "function",
                        "function": {
                            "name": b.get("name"),
                            "arguments": json.dumps(b.get("input") or {}),
                        },
                    }
                    for b in content
                    if b.get("type") == "tool_use"
                ]
                converted = {"role": "assistant", "content": "\n".join(text_parts) or None}
                if tool_calls:
                    converted["tool_calls"] = tool_calls
                openai_messages.append(converted)
                continue

            if role == "user" and isinstance(content, list):
                # OpenAI expects tool results directly after the assistant
                # tool_calls message, before any follow-up user text.
                for block in content:
                    if block.get("type") == "tool_result":
                        result_content = block.get("content")
                        if not isinstance(result_content, str):
                            result_content = json.dumps(result_content)
                        openai_messages.append({
                            "role": "tool",
                            "tool_call_id": block.get("tool_use_id"),
                            "content": result_content,
                        })
                text_parts = [b.get("text", "") for b in content if b.get("type") == "text"]
                if text_parts:
                    openai_messages.append({"role": "user", "content": "\n".join(text_parts)})
                continue

            openai_messages.append({"role": role, "content": content})

        return openai_messages

    def _convert_tools_to_openai(self, anthropic_tools: list[dict]) -> list[dict]:
        """Convert Anthropic tool format to OpenAI format."""
        openai_tools = []
        for tool in anthropic_tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("input_schema", {})
                }
            })
        return openai_tools

    def is_available(self) -> dict:
        """Check which providers are available."""
        return {
            "claude": self.claude_client is not None,
            "nararouter": self.nararouter_client is not None
        }