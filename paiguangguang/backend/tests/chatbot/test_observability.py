from __future__ import annotations

import json

from app.chatbot.observability import build_chatbot_event_payload, build_content_fingerprint, log_chatbot_event
from app.core import logging as logging_module


def test_build_content_fingerprint_is_deterministic_and_length_bound() -> None:
    fingerprint_a = build_content_fingerprint("请总结当前架构选择")
    fingerprint_b = build_content_fingerprint("请总结当前架构选择")

    assert fingerprint_a == fingerprint_b
    assert fingerprint_a["content_length"] == len("请总结当前架构选择")
    assert len(fingerprint_a["content_hash"]) == 16


def test_log_chatbot_event_hashes_user_and_does_not_emit_plaintext(monkeypatch) -> None:
    captured: list[str] = []
    monkeypatch.setattr(logging_module._LOGGER, "info", lambda message: captured.append(message))

    log_chatbot_event(
        "chatbot.request.completed",
        request_id="0198a6f0-5c62-7ba1-a682-22f731c33545",
        user_id="1a2b3c4d-5e6f-7081-92ab-3c4d5e6f7081",
        conversation_id="2a2b3c4d-5e6f-7081-92ab-3c4d5e6f7082",
        assistant_message_id="3a2b3c4d-5e6f-7081-92ab-3c4d5e6f7083",
        llm_run_id="4a2b3c4d-5e6f-7081-92ab-3c4d5e6f7084",
        provider="deepseek",
        model="deepseek-chat",
        status="completed",
        latency_ms=1234,
        first_token_latency_ms=321,
        prompt_tokens=10,
        completion_tokens=20,
        total_tokens=30,
        content="模型输出正文",
    )

    assert len(captured) == 1
    payload = json.loads(captured[0])

    assert payload["event"] == "chatbot.request.completed"
    assert payload["request_id"] == "0198a6f0-5c62-7ba1-a682-22f731c33545"
    assert payload["user_id_hash"] != "1a2b3c4d-5e6f-7081-92ab-3c4d5e6f7081"
    assert payload["conversation_id"] == "2a2b3c4d-5e6f-7081-92ab-3c4d5e6f7082"
    assert payload["assistant_message_id"] == "3a2b3c4d-5e6f-7081-92ab-3c4d5e6f7083"
    assert payload["llm_run_id"] == "4a2b3c4d-5e6f-7081-92ab-3c4d5e6f7084"
    assert payload["provider"] == "deepseek"
    assert payload["model"] == "deepseek-chat"
    assert payload["status"] == "completed"
    assert payload["latency_ms"] == 1234
    assert payload["first_token_latency_ms"] == 321
    assert payload["prompt_tokens"] == 10
    assert payload["completion_tokens"] == 20
    assert payload["total_tokens"] == 30
    assert payload["content_length"] == len("模型输出正文")
    assert len(payload["content_hash"]) == 16
    assert "模型输出正文" not in captured[0]


def test_build_chatbot_event_payload_exposes_expected_fields() -> None:
    payload = build_chatbot_event_payload(
        "chatbot.memory.backlog",
        request_id="req-1",
        user_id="user-1",
        conversation_id="conv-1",
        message_id="msg-1",
        llm_run_id="run-1",
        hits=3,
        status="pending",
        error_code=None,
        source="postgres",
    )

    assert payload["event"] == "chatbot.memory.backlog"
    assert payload["request_id"] == "req-1"
    assert payload["user_id_hash"]
    assert payload["conversation_id"] == "conv-1"
    assert payload["message_id"] == "msg-1"
    assert payload["llm_run_id"] == "run-1"
    assert payload["hits"] == 3
    assert payload["status"] == "pending"
    assert payload["source"] == "postgres"
