from __future__ import annotations

import json

from app.chatbot.observability import log_chatbot_event
from app.core import logging as logging_module


def test_chatbot_logging_does_not_emit_plaintext_prompt_or_secret_values(monkeypatch) -> None:
    captured: list[str] = []
    monkeypatch.setattr(logging_module._LOGGER, "info", lambda message: captured.append(message))

    log_chatbot_event(
        "chatbot.stream.failed",
        request_id="0198a6f0-5c62-7ba1-a682-22f731c33545",
        user_id="user-plain-text",
        content="system prompt: keep secrets out",
        provider="deepseek",
        model="deepseek-chat",
        error_code="CHATBOT_LLM_TIMEOUT",
        status="failed",
        reason="LLMTimeoutError",
        source="provider",
        extra={
            "authorization": "Bearer secret-token",
            "api_key": "key-123",
            "redis_url": "redis://user:pass@redis.internal:6379/0",
            "prompt": "do not log this",
        },
    )

    assert len(captured) == 1
    payload = json.loads(captured[0])

    assert payload["user_id_hash"] != "user-plain-text"
    assert payload["content_length"] == len("system prompt: keep secrets out")
    assert len(payload["content_hash"]) == 16
    assert payload["authorization"] == "[redacted]"
    assert payload["api_key"] == "[redacted]"
    assert payload["redis_url"] == "[redacted]"
    assert payload["prompt"] == "[redacted]"
    assert "system prompt: keep secrets out" not in captured[0]
    assert "Bearer secret-token" not in captured[0]
