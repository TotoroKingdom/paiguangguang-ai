from __future__ import annotations

from app.chatbot.errors import CHATBOT_ERROR_SPECS, get_chatbot_error_spec, is_chatbot_error_retryable


def test_chatbot_error_spec_covers_documented_http_codes() -> None:
    expected_codes = {
        "CHATBOT_INVALID_CURSOR",
        "CHATBOT_IDEMPOTENCY_KEY_MISMATCH",
        "CHATBOT_CONVERSATION_NOT_FOUND",
        "CHATBOT_MESSAGE_NOT_FOUND",
        "CHATBOT_MEMORY_NOT_FOUND",
        "CHATBOT_CONVERSATION_BUSY",
        "CHATBOT_REQUEST_IN_PROGRESS",
        "CHATBOT_IDEMPOTENCY_CONFLICT",
        "CHATBOT_NO_ACTIVE_GENERATION",
        "CHATBOT_MESSAGE_NOT_RETRYABLE",
        "CHATBOT_REGENERATE_NOT_LATEST_TURN",
        "CHATBOT_MEMORY_CONFLICT",
        "VALIDATION_ERROR",
        "CHATBOT_MODEL_NOT_ALLOWED",
        "CHATBOT_RATE_LIMITED",
        "CHATBOT_LLM_PROVIDER_ERROR",
        "CHATBOT_LLM_TIMEOUT",
        "CHATBOT_STREAM_ERROR",
        "CHATBOT_INTERNAL_ERROR",
    }

    assert expected_codes.issubset(CHATBOT_ERROR_SPECS.keys())


def test_chatbot_error_spec_returns_known_retryability() -> None:
    assert get_chatbot_error_spec("CHATBOT_CONVERSATION_BUSY").retryable is True
    assert get_chatbot_error_spec("CHATBOT_REQUEST_IN_PROGRESS").retryable is False
    assert get_chatbot_error_spec("CHATBOT_LLM_TIMEOUT").retryable is True
    assert get_chatbot_error_spec("CHATBOT_MODEL_NOT_ALLOWED").retryable is False
    assert is_chatbot_error_retryable("CHATBOT_RATE_LIMITED") is True
    assert is_chatbot_error_retryable("UNKNOWN_CODE") is False


def test_unknown_chatbot_error_code_uses_internal_fallback() -> None:
    spec = get_chatbot_error_spec("CHATBOT_DOES_NOT_EXIST")

    assert spec.status_code == 500
    assert spec.code == "CHATBOT_INTERNAL_ERROR"
    assert spec.retryable is False
