from __future__ import annotations

import hashlib
import json
import logging
from typing import Any
from urllib.parse import urlsplit, urlunsplit


_LOGGER = logging.getLogger("paiguangguang.backend")
_REDACTED = "[redacted]"
_SENSITIVE_KEYS = {
    "authorization",
    "api_key",
    "api-key",
    "token",
    "password",
    "secret",
    "jwt",
    "access_token",
    "refresh_token",
    "redis_url",
}


def _is_sensitive_key(key: Any) -> bool:
    normalized = str(key).strip().lower()
    return normalized in _SENSITIVE_KEYS or normalized.endswith("_url")


def _redact_url(value: str) -> str:
    try:
        parts = urlsplit(value)
    except ValueError:
        return _REDACTED

    if not parts.scheme or not parts.netloc:
        return value

    if parts.username is None and parts.password is None:
        return value

    hostname = parts.hostname or ""
    if not hostname:
        return _REDACTED
    if parts.port is not None:
        hostname = f"{hostname}:{parts.port}"

    return urlunsplit((parts.scheme, f"***:***@{hostname}", parts.path, parts.query, parts.fragment))


def _json_safe(value: Any, *, key: str | None = None) -> Any:
    if key is not None and _is_sensitive_key(key):
        return _REDACTED
    if isinstance(value, dict):
        return {str(child_key): _json_safe(item, key=str(child_key)) for child_key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, set):
        return sorted((_json_safe(item) for item in value), key=repr)
    if isinstance(value, str):
        return _redact_url(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def log_event(event: str, **fields: Any) -> None:
    payload = {"event": event, **{key: _json_safe(value, key=str(key)) for key, value in fields.items()}}
    _LOGGER.info(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def stable_hash(value: str, *, length: int = 16) -> str:
    if length < 1:
        raise ValueError("length must be positive")
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return digest[:length]
