from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ChatbotErrorSpec:
    code: str
    status_code: int
    message: str
    retryable: bool


CHATBOT_ERROR_SPECS: dict[str, ChatbotErrorSpec] = {
    "CHATBOT_INVALID_CURSOR": ChatbotErrorSpec(
        code="CHATBOT_INVALID_CURSOR",
        status_code=400,
        message="Invalid cursor",
        retryable=False,
    ),
    "CHATBOT_IDEMPOTENCY_KEY_MISMATCH": ChatbotErrorSpec(
        code="CHATBOT_IDEMPOTENCY_KEY_MISMATCH",
        status_code=400,
        message="Idempotency-Key must match client_request_id",
        retryable=False,
    ),
    "CHATBOT_CONVERSATION_NOT_FOUND": ChatbotErrorSpec(
        code="CHATBOT_CONVERSATION_NOT_FOUND",
        status_code=404,
        message="Conversation not found",
        retryable=False,
    ),
    "CHATBOT_MESSAGE_NOT_FOUND": ChatbotErrorSpec(
        code="CHATBOT_MESSAGE_NOT_FOUND",
        status_code=404,
        message="Message not found",
        retryable=False,
    ),
    "CHATBOT_MEMORY_NOT_FOUND": ChatbotErrorSpec(
        code="CHATBOT_MEMORY_NOT_FOUND",
        status_code=404,
        message="Memory not found",
        retryable=False,
    ),
    "CHATBOT_CONVERSATION_BUSY": ChatbotErrorSpec(
        code="CHATBOT_CONVERSATION_BUSY",
        status_code=409,
        message="Conversation is busy",
        retryable=True,
    ),
    "CHATBOT_REQUEST_IN_PROGRESS": ChatbotErrorSpec(
        code="CHATBOT_REQUEST_IN_PROGRESS",
        status_code=409,
        message="Request is already running",
        retryable=False,
    ),
    "CHATBOT_IDEMPOTENCY_CONFLICT": ChatbotErrorSpec(
        code="CHATBOT_IDEMPOTENCY_CONFLICT",
        status_code=409,
        message="Idempotency conflict",
        retryable=False,
    ),
    "CHATBOT_NO_ACTIVE_GENERATION": ChatbotErrorSpec(
        code="CHATBOT_NO_ACTIVE_GENERATION",
        status_code=409,
        message="Conversation has no active generation",
        retryable=False,
    ),
    "CHATBOT_MESSAGE_NOT_RETRYABLE": ChatbotErrorSpec(
        code="CHATBOT_MESSAGE_NOT_RETRYABLE",
        status_code=409,
        message="Message is not retryable",
        retryable=False,
    ),
    "CHATBOT_REGENERATE_NOT_LATEST_TURN": ChatbotErrorSpec(
        code="CHATBOT_REGENERATE_NOT_LATEST_TURN",
        status_code=409,
        message="Regenerate requires the latest user turn",
        retryable=False,
    ),
    "CHATBOT_MEMORY_CONFLICT": ChatbotErrorSpec(
        code="CHATBOT_MEMORY_CONFLICT",
        status_code=409,
        message="Memory conflicts with an active memory",
        retryable=False,
    ),
    "VALIDATION_ERROR": ChatbotErrorSpec(
        code="VALIDATION_ERROR",
        status_code=422,
        message="Request validation failed",
        retryable=False,
    ),
    "CHATBOT_MODEL_NOT_ALLOWED": ChatbotErrorSpec(
        code="CHATBOT_MODEL_NOT_ALLOWED",
        status_code=422,
        message="Model is not allowed",
        retryable=False,
    ),
    "CHATBOT_RATE_LIMITED": ChatbotErrorSpec(
        code="CHATBOT_RATE_LIMITED",
        status_code=429,
        message="Request was rate limited",
        retryable=True,
    ),
    "CHATBOT_LLM_PROVIDER_ERROR": ChatbotErrorSpec(
        code="CHATBOT_LLM_PROVIDER_ERROR",
        status_code=502,
        message="LLM provider request failed",
        retryable=True,
    ),
    "CHATBOT_LLM_TIMEOUT": ChatbotErrorSpec(
        code="CHATBOT_LLM_TIMEOUT",
        status_code=504,
        message="Generation timed out",
        retryable=True,
    ),
    "CHATBOT_STREAM_ERROR": ChatbotErrorSpec(
        code="CHATBOT_STREAM_ERROR",
        status_code=500,
        message="Internal stream processing failed",
        retryable=True,
    ),
    "CHATBOT_INTERNAL_ERROR": ChatbotErrorSpec(
        code="CHATBOT_INTERNAL_ERROR",
        status_code=500,
        message="Internal server error",
        retryable=True,
    ),
    "CHATBOT_LLM_RATE_LIMITED": ChatbotErrorSpec(
        code="CHATBOT_LLM_RATE_LIMITED",
        status_code=429,
        message="Generation was rate limited",
        retryable=True,
    ),
    "CHATBOT_LLM_PROTOCOL_ERROR": ChatbotErrorSpec(
        code="CHATBOT_LLM_PROTOCOL_ERROR",
        status_code=500,
        message="LLM returned an invalid response",
        retryable=True,
    ),
    "CHATBOT_LLM_CONFIGURATION_ERROR": ChatbotErrorSpec(
        code="CHATBOT_LLM_CONFIGURATION_ERROR",
        status_code=500,
        message="LLM provider is misconfigured",
        retryable=False,
    ),
    "CHATBOT_LLM_INTERNAL_ERROR": ChatbotErrorSpec(
        code="CHATBOT_LLM_INTERNAL_ERROR",
        status_code=500,
        message="LLM request failed",
        retryable=True,
    ),
    "CHATBOT_CHAT_STATE_CORRUPTED": ChatbotErrorSpec(
        code="CHATBOT_CHAT_STATE_CORRUPTED",
        status_code=500,
        message="Chat state is inconsistent",
        retryable=False,
    ),
    "CHATBOT_MESSAGE_TOO_LONG": ChatbotErrorSpec(
        code="CHATBOT_MESSAGE_TOO_LONG",
        status_code=422,
        message="Content is too long",
        retryable=False,
    ),
    "CHATBOT_STALE_GENERATION": ChatbotErrorSpec(
        code="CHATBOT_STALE_GENERATION",
        status_code=500,
        message="Generation expired before completion",
        retryable=False,
    ),
    "CHATBOT_STREAM_CLIENT_DISCONNECTED": ChatbotErrorSpec(
        code="CHATBOT_STREAM_CLIENT_DISCONNECTED",
        status_code=499,
        message="Client disconnected while streaming",
        retryable=True,
    ),
}

_UNKNOWN_ERROR_SPEC = ChatbotErrorSpec(
    code="CHATBOT_INTERNAL_ERROR",
    status_code=500,
    message="Internal server error",
    retryable=False,
)


class ChatbotApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str, details: Any | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


def get_chatbot_error_spec(code: str) -> ChatbotErrorSpec:
    return CHATBOT_ERROR_SPECS.get(code, _UNKNOWN_ERROR_SPEC)


def is_chatbot_error_retryable(code: str) -> bool:
    return get_chatbot_error_spec(code).retryable
