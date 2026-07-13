from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
from typing import Any

from app.core.config import Settings, get_settings

try:  # Optional dependency for configured Redis-backed memory.
    import redis  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    redis = None


_KEY_COMPONENT_RE = re.compile(r"[^A-Za-z0-9_.:-]+")


def _normalize_key_component(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        return "unknown"
    return _KEY_COMPONENT_RE.sub("_", normalized)


def build_short_term_memory_key(
    *,
    environment: str,
    schema_version: int,
    user_id: str,
    conversation_id: str,
    memory_type: str,
) -> str:
    return ":".join(
        [
            "chatbot",
            _normalize_key_component(environment),
            f"v{schema_version}",
            f"user:{_normalize_key_component(user_id)}",
            f"conversation:{_normalize_key_component(conversation_id)}",
            _normalize_key_component(memory_type),
        ]
    )


@dataclass(frozen=True, slots=True)
class RedisShortTermMemoryAdapter:
    redis_url: str
    environment: str
    schema_version: int
    prefix: str = "chatbot"
    redis_module: Any | None = None
    _client: Any = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        redis_impl = self.redis_module if self.redis_module is not None else redis
        if redis_impl is None:  # pragma: no cover - optional dependency
            raise RuntimeError("redis package is not installed")
        object.__setattr__(self, "_client", redis_impl.from_url(self.redis_url, decode_responses=True))
        self._client.ping()

    def _key(self, *, user_id: str, conversation_id: str, memory_type: str) -> str:
        return build_short_term_memory_key(
            environment=self.environment,
            schema_version=self.schema_version,
            user_id=user_id,
            conversation_id=conversation_id,
            memory_type=memory_type,
        )

    def get(self, *, user_id: str, conversation_id: str, memory_type: str) -> Any | None:
        payload = self._client.get(self._key(user_id=user_id, conversation_id=conversation_id, memory_type=memory_type))
        if payload is None:
            return None
        return json.loads(payload)

    def set(
        self,
        *,
        user_id: str,
        conversation_id: str,
        memory_type: str,
        value: Any,
        ttl_seconds: int | None = None,
    ) -> None:
        payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
        key = self._key(user_id=user_id, conversation_id=conversation_id, memory_type=memory_type)
        if ttl_seconds is not None:
            self._client.setex(key, ttl_seconds, payload)
            return
        self._client.set(key, payload)

    def delete(self, *, user_id: str, conversation_id: str, memory_type: str) -> None:
        self._client.delete(self._key(user_id=user_id, conversation_id=conversation_id, memory_type=memory_type))
