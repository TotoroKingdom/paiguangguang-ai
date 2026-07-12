from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import re
from threading import Lock
from typing import Any, Protocol

from app.core.config import Settings, get_settings
from app.core.logging import log_event

try:  # Optional dependency for configured Redis-backed cache.
    import redis  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    redis = None


_CACHE_ROOT_PREFIX = "paiguangguang:cache"
_KEY_COMPONENT_RE = re.compile(r"[^A-Za-z0-9_.:-]+")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_key_component(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        return "unknown"
    return _KEY_COMPONENT_RE.sub("_", normalized)


def build_request_hash(payload: Any) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return sha256(serialized.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CacheKeyContext:
    user_identity: str
    permission_scope: str
    workspace_id: str
    knowledge_base_version: str
    retrieval_strategy_version: str
    model_version: str
    request_hash: str


def build_cache_key(namespace: str, context: CacheKeyContext) -> str:
    namespace = namespace.strip().strip(":") or "default"
    return ":".join(
        [
            _CACHE_ROOT_PREFIX,
            namespace,
            f"user={_normalize_key_component(context.user_identity)}",
            f"scope={_normalize_key_component(context.permission_scope)}",
            f"workspace={_normalize_key_component(context.workspace_id)}",
            f"kb={_normalize_key_component(context.knowledge_base_version)}",
            f"strategy={_normalize_key_component(context.retrieval_strategy_version)}",
            f"model={_normalize_key_component(context.model_version)}",
            f"request={_normalize_key_component(context.request_hash)}",
        ]
    )


def build_entity_cache_key(
    namespace: str,
    *,
    entity: str,
    kind: str,
    entity_id: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
    sort_by: str | None = None,
    sort_order: str | None = None,
    user_id: str | None = None,
) -> str:
    parts = [_CACHE_ROOT_PREFIX, _normalize_key_component(namespace), _normalize_key_component(entity), _normalize_key_component(kind)]
    if entity_id is not None:
        parts.append(f"id={_normalize_key_component(entity_id)}")
    if page is not None:
        parts.append(f"page={page}")
    if page_size is not None:
        parts.append(f"page_size={page_size}")
    if sort_by is not None:
        parts.append(f"sort_by={_normalize_key_component(sort_by)}")
    if sort_order is not None:
        parts.append(f"sort_order={_normalize_key_component(sort_order)}")
    if user_id is not None:
        parts.append(f"user={_normalize_key_component(user_id)}")
    return ":".join(parts)


def build_entity_cache_prefix(namespace: str, *, entity: str, kind: str | None = None) -> str:
    parts = [_CACHE_ROOT_PREFIX, _normalize_key_component(namespace), _normalize_key_component(entity)]
    if kind is not None:
        parts.append(_normalize_key_component(kind))
    return ":".join(parts)


def build_auth_user_context_cache_key(user_id: str) -> str:
    return ":".join(
        [
            _CACHE_ROOT_PREFIX,
            "auth",
            "user-context",
            f"user={_normalize_key_component(user_id)}",
        ]
    )


def build_admin_list_cache_key(
    entity: str,
    *,
    page: int,
    page_size: int,
    sort_by: str,
    sort_order: str,
) -> str:
    return ":".join(
        [
            _CACHE_ROOT_PREFIX,
            "admin",
            _normalize_key_component(entity),
            "list",
            f"page={page}",
            f"page_size={page_size}",
            f"sort_by={_normalize_key_component(sort_by)}",
            f"sort_order={_normalize_key_component(sort_order)}",
        ]
    )


def build_admin_detail_cache_key(entity: str, entity_id: str) -> str:
    return ":".join(
        [
            _CACHE_ROOT_PREFIX,
            "admin",
            _normalize_key_component(entity),
            "detail",
            f"id={_normalize_key_component(entity_id)}",
        ]
    )


class CacheAdapter(Protocol):
    backend_name: str

    def get(self, key: str) -> Any | None:
        ...

    def set(self, key: str, value: Any, *, ttl_seconds: int | None = None) -> None:
        ...

    def delete(self, key: str) -> None:
        ...

    def delete_prefix(self, prefix: str) -> None:
        ...


class InMemoryCacheAdapter:
    backend_name = "memory"

    def __init__(self) -> None:
        self._values: dict[str, tuple[str, datetime | None]] = {}
        self._lock = Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            record = self._values.get(key)
            if record is None:
                return None
            payload, expires_at = record
            if expires_at is not None and expires_at <= _utcnow():
                self._values.pop(key, None)
                return None
        return json.loads(payload)

    def set(self, key: str, value: Any, *, ttl_seconds: int | None = None) -> None:
        payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
        expires_at = _utcnow() + timedelta(seconds=ttl_seconds) if ttl_seconds is not None else None
        with self._lock:
            self._values[key] = (payload, expires_at)

    def delete(self, key: str) -> None:
        with self._lock:
            self._values.pop(key, None)

    def delete_prefix(self, prefix: str) -> None:
        normalized_prefix = prefix.strip().strip(":")
        with self._lock:
            keys = [
                key
                for key in self._values
                if key.startswith(normalized_prefix) or key.startswith(f"{_CACHE_ROOT_PREFIX}:{normalized_prefix}")
            ]
            for key in keys:
                self._values.pop(key, None)


class RedisCacheAdapter:
    backend_name = "redis"

    def __init__(
        self,
        redis_url: str,
        *,
        prefix: str = _CACHE_ROOT_PREFIX,
        redis_module: Any | None = None,
    ) -> None:
        redis_impl = redis_module if redis_module is not None else redis
        if redis_impl is None:  # pragma: no cover - optional dependency
            raise RuntimeError("redis package is not installed")
        self._client = redis_impl.from_url(redis_url, decode_responses=True)
        self._redis_url = redis_url
        self._prefix = prefix.rstrip(":")
        self._client.ping()

    def _namespaced_key(self, key: str) -> str:
        return f"{self._prefix}:{key}"

    def get(self, key: str) -> Any | None:
        payload = self._client.get(self._namespaced_key(key))
        if payload is None:
            return None
        return json.loads(payload)

    def set(self, key: str, value: Any, *, ttl_seconds: int | None = None) -> None:
        payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
        namespaced_key = self._namespaced_key(key)
        if ttl_seconds is not None:
            self._client.setex(namespaced_key, ttl_seconds, payload)
            return
        self._client.set(namespaced_key, payload)

    def delete(self, key: str) -> None:
        self._client.delete(self._namespaced_key(key))

    def delete_prefix(self, prefix: str) -> None:
        normalized_prefix = prefix.strip().strip(":")
        pattern = self._namespaced_key(normalized_prefix)
        keys = self._client.keys(f"{pattern}*")
        if keys:
            self._client.delete(*keys)


_IN_MEMORY_CACHE_ADAPTER = InMemoryCacheAdapter()
_REDIS_CACHE_ADAPTER: RedisCacheAdapter | None = None
_ACTIVE_CACHE_BACKEND: str | None = None


def get_cache_adapter(settings: Settings | None = None) -> CacheAdapter:
    global _REDIS_CACHE_ADAPTER, _ACTIVE_CACHE_BACKEND

    settings = settings or get_settings()
    if settings.redis_url:
        try:
            if _REDIS_CACHE_ADAPTER is None or getattr(_REDIS_CACHE_ADAPTER, "_redis_url", None) != settings.redis_url:
                _REDIS_CACHE_ADAPTER = RedisCacheAdapter(settings.redis_url)
            if _ACTIVE_CACHE_BACKEND != _REDIS_CACHE_ADAPTER.backend_name:
                _ACTIVE_CACHE_BACKEND = _REDIS_CACHE_ADAPTER.backend_name
                log_event("cache.backend_selected", backend=_ACTIVE_CACHE_BACKEND)
            return _REDIS_CACHE_ADAPTER
        except Exception:
            if _ACTIVE_CACHE_BACKEND != _IN_MEMORY_CACHE_ADAPTER.backend_name:
                _ACTIVE_CACHE_BACKEND = _IN_MEMORY_CACHE_ADAPTER.backend_name
                log_event("cache.backend_selected", backend=_ACTIVE_CACHE_BACKEND)
            return _IN_MEMORY_CACHE_ADAPTER
    if _ACTIVE_CACHE_BACKEND != _IN_MEMORY_CACHE_ADAPTER.backend_name:
        _ACTIVE_CACHE_BACKEND = _IN_MEMORY_CACHE_ADAPTER.backend_name
        log_event("cache.backend_selected", backend=_ACTIVE_CACHE_BACKEND)
    return _IN_MEMORY_CACHE_ADAPTER


def get_active_cache_backend(settings: Settings | None = None) -> str:
    adapter = get_cache_adapter(settings)
    return adapter.backend_name
