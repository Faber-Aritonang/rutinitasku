"""Tests for Gradio chat event handlers."""

import pytest

import app


class FakeOrchestrator:
    def create_session(self):
        return "test-session"

    async def chat_stream(self, message, session_id):
        assert message == "Halo"
        assert session_id == "test-session"
        yield "Hai"
        yield "!"


@pytest.mark.asyncio
async def test_stream_chat_response_keeps_user_and_assistant_messages(monkeypatch):
    monkeypatch.setattr(app, "orchestrator", FakeOrchestrator())

    updates = [
        update async for update in app.stream_chat_response("Halo", [], "")
    ]

    assert updates[0] == [
        {"role": "user", "content": "Halo"},
        {"role": "assistant", "content": ""},
    ]
    assert updates[1][-1] == {"role": "assistant", "content": "Hai▌"}
    assert updates[2][-1] == {"role": "assistant", "content": "Hai!▌"}
    assert updates[-1] == [
        {"role": "user", "content": "Halo"},
        {"role": "assistant", "content": "Hai!"},
    ]
