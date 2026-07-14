from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from threading import Lock
from typing import Any

from app.core.config import Settings, get_settings
from app.chatbot.observability import log_chatbot_event

try:  # Optional dependency when Redis is configured.
    import redis  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    redis = None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_component(value: str) -> str:
    normalized = value.strip()
    return normalized or "unknown"


@dataclass(frozen=True, slots=True)
class CancellationRecord:
    conversation_id: str
    assistant_message_id: str
    status: str
    requested_at: datetime


class CancellationService:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        redis_module: Any | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._redis_url = self.settings.redis_url.strip()
        self._ttl_seconds = max(300, int(self.settings.chatbot_llm_timeout_seconds) + 60)
        self._redis_module = redis_module if redis_module is not None else redis
        self._client = None
        self._memory_store: dict[str, str] = {}
        self._lock = Lock()
        if self._redis_url and self._redis_module is not None:
            try:
                self._client = self._redis_module.from_url(self._redis_url, decode_responses=True)
                self._client.ping()
            except Exception as exc:
                self._degrade("ping", exc)

    def _degrade(self, operation: str, exc: Exception) -> None:
        self._client = None
        log_chatbot_event(
            "chatbot.redis.degraded",
            source="cancellation",
            reason=type(exc).__name__,
            status="memory_fallback",
            extra={"operation": operation},
        )

    @staticmethod
    def build_key(conversation_id: str, assistant_message_id: str) -> str:
        return ":".join(
            [
                "chatbot",
                "generation",
                "cancel",
                f"conversation={_normalize_component(conversation_id)}",
                f"assistant={_normalize_component(assistant_message_id)}",
            ]
        )

    def _serialize(self, record: CancellationRecord) -> str:
        return json.dumps(
            {
                "conversation_id": record.conversation_id,
                "assistant_message_id": record.assistant_message_id,
                "status": record.status,
                "requested_at": record.requested_at.isoformat(),
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

    def _deserialize(self, payload: str) -> CancellationRecord | None:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return None
        if not isinstance(data, dict):
            return None
        conversation_id = data.get("conversation_id")
        assistant_message_id = data.get("assistant_message_id")
        status = data.get("status")
        requested_at = data.get("requested_at")
        if not all(isinstance(value, str) for value in (conversation_id, assistant_message_id, status, requested_at)):
            return None
        try:
            parsed_requested_at = datetime.fromisoformat(requested_at)
        except ValueError:
            parsed_requested_at = _utcnow()
        return CancellationRecord(
            conversation_id=conversation_id,
            assistant_message_id=assistant_message_id,
            status=status,
            requested_at=parsed_requested_at,
        )

    def get(self, conversation_id: str, assistant_message_id: str) -> CancellationRecord | None:
        key = self.build_key(conversation_id, assistant_message_id)
        if self._client is not None:
            try:
                payload = self._client.get(key)
                return self._deserialize(payload) if isinstance(payload, str) else None
            except Exception as exc:
                self._degrade("get", exc)
        with self._lock:
            payload = self._memory_store.get(key)
        return self._deserialize(payload) if payload is not None else None

    def request_stop(self, conversation_id: str, assistant_message_id: str) -> CancellationRecord:
        key = self.build_key(conversation_id, assistant_message_id)
        record = CancellationRecord(
            conversation_id=conversation_id,
            assistant_message_id=assistant_message_id,
            status="cancellation_requested",
            requested_at=_utcnow(),
        )
        payload = self._serialize(record)

        if self._client is not None:
            try:
                stored = self._client.set(key, payload, nx=True, px=self._ttl_seconds * 1000)
                if not stored:
                    current = self.get(conversation_id, assistant_message_id)
                    return current or record
                return record
            except Exception as exc:
                self._degrade("set", exc)

        with self._lock:
            existing = self._memory_store.get(key)
            if existing is None:
                self._memory_store[key] = payload
                return record
        current = self._deserialize(existing)
        return current or record

    def is_requested(self, conversation_id: str, assistant_message_id: str) -> bool:
        return self.get(conversation_id, assistant_message_id) is not None

    def clear(self, conversation_id: str, assistant_message_id: str) -> None:
        key = self.build_key(conversation_id, assistant_message_id)
        if self._client is not None:
            try:
                self._client.delete(key)
                return
            except Exception as exc:
                self._degrade("delete", exc)
        with self._lock:
            self._memory_store.pop(key, None)


_CANCELLATION_SERVICE: CancellationService | None = None


def get_cancellation_service() -> CancellationService:
    global _CANCELLATION_SERVICE
    if _CANCELLATION_SERVICE is None:
        _CANCELLATION_SERVICE = CancellationService()
    return _CANCELLATION_SERVICE
