from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from threading import Lock
from typing import Any
from uuid import uuid4

from app.core.config import Settings, get_settings

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
class ConcurrencyLease:
    conversation_id: str
    user_id: str
    owner_token: str
    acquired_at: datetime
    expires_at: datetime
    backend: str


class ConcurrencyService:
    RELEASE_SCRIPT = """
local current = redis.call('get', KEYS[1])
if current == ARGV[1] then
  return redis.call('del', KEYS[1])
end
return 0
"""
    RENEW_SCRIPT = """
local current = redis.call('get', KEYS[1])
if current == ARGV[1] then
  return redis.call('pexpire', KEYS[1], ARGV[2])
end
return 0
"""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        redis_module: Any | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._ttl_seconds = max(1, int(self.settings.chatbot_lock_ttl_seconds))
        self._redis_url = self.settings.redis_url.strip()
        self._redis_module = redis_module if redis_module is not None else redis
        self._client = None
        self._memory_locks: dict[str, ConcurrencyLease] = {}
        self._lock = Lock()
        if self._redis_url and self._redis_module is not None:
            try:
                self._client = self._redis_module.from_url(self._redis_url, decode_responses=True)
                self._client.ping()
            except Exception:
                self._client = None

    @staticmethod
    def build_key(conversation_id: str, user_id: str) -> str:
        return ":".join(
            [
                "chatbot",
                "lock",
                f"conversation={_normalize_component(conversation_id)}",
                f"user={_normalize_component(user_id)}",
            ]
        )

    def _build_lease(self, conversation_id: str, user_id: str, owner_token: str) -> ConcurrencyLease:
        acquired_at = _utcnow()
        return ConcurrencyLease(
            conversation_id=conversation_id,
            user_id=user_id,
            owner_token=owner_token,
            acquired_at=acquired_at,
            expires_at=acquired_at + timedelta(seconds=self._ttl_seconds),
            backend=self.backend_name,
        )

    @property
    def backend_name(self) -> str:
        return "redis" if self._client is not None else "memory"

    def acquire(self, conversation_id: str, user_id: str) -> ConcurrencyLease | None:
        key = self.build_key(conversation_id, user_id)
        owner_token = str(uuid4())
        if self._client is not None:
            stored = self._client.set(key, owner_token, nx=True, px=self._ttl_seconds * 1000)
            if not stored:
                return None
            return self._build_lease(conversation_id, user_id, owner_token)

        now = _utcnow()
        with self._lock:
            current = self._memory_locks.get(key)
            if current is not None and current.expires_at > now:
                return None
            if current is not None and current.expires_at <= now:
                self._memory_locks.pop(key, None)
            lease = self._build_lease(conversation_id, user_id, owner_token)
            self._memory_locks[key] = lease
            return lease

    def renew(self, lease: ConcurrencyLease) -> bool:
        key = self.build_key(lease.conversation_id, lease.user_id)
        if self._client is not None:
            result = self._client.eval(self.RENEW_SCRIPT, 1, key, lease.owner_token, str(self._ttl_seconds * 1000))
            return bool(result)

        now = _utcnow()
        with self._lock:
            current = self._memory_locks.get(key)
            if current is None or current.owner_token != lease.owner_token or current.expires_at <= now:
                return False
            refreshed = ConcurrencyLease(
                conversation_id=lease.conversation_id,
                user_id=lease.user_id,
                owner_token=lease.owner_token,
                acquired_at=current.acquired_at,
                expires_at=now + timedelta(seconds=self._ttl_seconds),
                backend=current.backend,
            )
            self._memory_locks[key] = refreshed
            return True

    def release(self, lease: ConcurrencyLease) -> bool:
        key = self.build_key(lease.conversation_id, lease.user_id)
        if self._client is not None:
            result = self._client.eval(self.RELEASE_SCRIPT, 1, key, lease.owner_token)
            return bool(result)

        with self._lock:
            current = self._memory_locks.get(key)
            if current is None or current.owner_token != lease.owner_token:
                return False
            self._memory_locks.pop(key, None)
            return True


_CONCURRENCY_SERVICE: ConcurrencyService | None = None


def get_concurrency_service() -> ConcurrencyService:
    global _CONCURRENCY_SERVICE
    if _CONCURRENCY_SERVICE is None:
        _CONCURRENCY_SERVICE = ConcurrencyService()
    return _CONCURRENCY_SERVICE
