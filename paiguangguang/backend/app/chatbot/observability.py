from __future__ import annotations

import re
from typing import Any, Mapping

from app.core.logging import log_event, stable_hash


_SENSITIVE_KEY_RE = re.compile(
    r"(authorization|api[_-]?key|token|password|secret|jwt|refresh[_-]?token|access[_-]?token|prompt|content|body|message|response|.*_url$)",
    re.IGNORECASE,
)
_REDACTED = "[redacted]"


def _is_sensitive_key(key: Any) -> bool:
    return bool(_SENSITIVE_KEY_RE.search(str(key).strip()))


def _sanitize_value(value: Any, *, key: str | None = None) -> Any:
    if key is not None and _is_sensitive_key(key):
        return _REDACTED
    if isinstance(value, dict):
        return {str(child_key): _sanitize_value(child_value, key=str(child_key)) for child_key, child_value in value.items()}
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, set):
        return sorted((_sanitize_value(item) for item in value), key=repr)
    return value


def build_content_fingerprint(content: str) -> dict[str, Any]:
    return {
        "content_length": len(content),
        "content_hash": stable_hash(content),
    }


def build_chatbot_event_payload(
    event: str,
    *,
    request_id: str | None = None,
    user_id: str | None = None,
    conversation_id: str | None = None,
    message_id: str | None = None,
    assistant_message_id: str | None = None,
    llm_run_id: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    status: str | None = None,
    error_code: str | None = None,
    latency_ms: int | None = None,
    first_token_latency_ms: int | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    total_tokens: int | None = None,
    hits: int | None = None,
    reason: str | None = None,
    source: str | None = None,
    content: str | None = None,
    content_length: int | None = None,
    content_hash: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"event": event}
    if request_id is not None:
        payload["request_id"] = request_id
    if user_id is not None:
        payload["user_id_hash"] = stable_hash(user_id)
    if conversation_id is not None:
        payload["conversation_id"] = conversation_id
    if message_id is not None:
        payload["message_id"] = message_id
    if assistant_message_id is not None:
        payload["assistant_message_id"] = assistant_message_id
    if llm_run_id is not None:
        payload["llm_run_id"] = llm_run_id
    if provider is not None:
        payload["provider"] = provider
    if model is not None:
        payload["model"] = model
    if status is not None:
        payload["status"] = status
    if error_code is not None:
        payload["error_code"] = error_code
    if latency_ms is not None:
        payload["latency_ms"] = latency_ms
    if first_token_latency_ms is not None:
        payload["first_token_latency_ms"] = first_token_latency_ms
    if prompt_tokens is not None:
        payload["prompt_tokens"] = prompt_tokens
    if completion_tokens is not None:
        payload["completion_tokens"] = completion_tokens
    if total_tokens is not None:
        payload["total_tokens"] = total_tokens
    if hits is not None:
        payload["hits"] = hits
    if reason is not None:
        payload["reason"] = reason
    if source is not None:
        payload["source"] = source

    if content is not None:
        payload.update(build_content_fingerprint(content))
    if content_length is not None:
        payload["content_length"] = content_length
    if content_hash is not None:
        payload["content_hash"] = content_hash

    if extra:
        for key, value in extra.items():
            payload[str(key)] = _sanitize_value(value, key=str(key))

    return payload


def log_chatbot_event(event: str, **fields: Any) -> None:
    payload = build_chatbot_event_payload(event, **fields)
    log_event(payload.pop("event"), **payload)
