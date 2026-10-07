"""
NaraTask AI - LLM Layer
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

        # Initialize Claude client
        if ANTHROPIC_API_KEY:
            self.claude_client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
            logger.info(f"Claude client initialized with model: {ANTHROPIC_MODEL}")

        # Initialize NaraRouter client
        if NARAROUTER_API_KEY:
            self.nararouter_client = AsyncOpenAI(
                api_key=NARAROUTER_API_KEY,
                base_url=NARAROUTER_BASE_URL
            )
            logger.info(f"NaraRouter client initialized with model: {NARAROUTER_MODEL}")

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
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat response with auto-fallback.

        Yields:
            Chunks of response text
        """
        # Try Claude first
        if self.claude_client:
            try:
                async for chunk in self._stream_claude(messages, tools, system):
                    yield chunk
                return
            except Exception as e:
                logger.warning(f"Claude streaming failed: {e}. Falling back to NaraRouter.")

        # Fallback to NaraRouter
        if self.nararouter_client:
            try:
                async for chunk in self._stream_nararouter(messages, tools, system):
                    yield chunk
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
            "temperature": TEMPERATURE
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
        # Convert messages format if needed
        openai_messages = []
        if system:
            openai_messages.append({"role": "system", "content": system})

        for msg in messages:
            openai_messages.append(msg)

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
                    "arguments": json.loads(tc.function.arguments)
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

    async def _stream_claude(
        self,
        messages: list[dict],
        tools: Optional[list[dict]],
        system: Optional[str]
    ) -> AsyncGenerator[str, None]:
        """Stream response from Claude."""
        kwargs = {
            "model": ANTHROPIC_MODEL,
            "max_tokens": MAX_TOKENS,
            "messages": messages,
            "temperature": TEMPERATURE
        }

        if system:
            kwargs["system"] = system

        if tools:
            kwargs["tools"] = tools

        async with self.claude_client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text

    async def _stream_nararouter(
        self,
        messages: list[dict],
        tools: Optional[list[dict]],
        system: Optional[str]
    ) -> AsyncGenerator[str, None]:
        """Stream response from NaraRouter."""
        openai_messages = []
        if system:
            openai_messages.append({"role": "system", "content": system})

        for msg in messages:
            openai_messages.append(msg)

        kwargs = {
            "model": NARAROUTER_MODEL,
            "messages": openai_messages,
            "max_tokens": MAX_TOKENS,
            "temperature": TEMPERATURE,
            "stream": True
        }

        if tools:
            openai_tools = self._convert_tools_to_openai(tools)
            kwargs["tools"] = openai_tools

        stream = await self.nararouter_client.chat.completions.create(**kwargs)

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

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