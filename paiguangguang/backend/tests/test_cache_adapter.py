from __future__ import annotations

from types import SimpleNamespace

from app.storage.cache import (
    CacheKeyContext,
    InMemoryCacheAdapter,
    RedisCacheAdapter,
    build_cache_key,
    build_request_hash,
    get_cache_adapter,
)


def test_in_memory_cache_adapter_supports_get_set_delete_and_prefix_removal() -> None:
    cache = InMemoryCacheAdapter()

    cache.set("rag:query:one", {"answer": "alpha", "count": 1})
    cache.set("rag:query:two", ["beta"])
    cache.set("other:thing", "gamma")

    assert cache.get("rag:query:one") == {"answer": "alpha", "count": 1}
    assert cache.get("rag:query:two") == ["beta"]

    cache.delete("rag:query:two")
    assert cache.get("rag:query:two") is None

    cache.delete_prefix("rag:query")
    assert cache.get("rag:query:one") is None
    assert cache.get("other:thing") == "gamma"


def test_cache_key_components_differ_across_identity_and_strategy_dimensions() -> None:
    base = CacheKeyContext(
        user_identity="user-1",
        permission_scope="workspace",
        workspace_id="workspace-a",
        knowledge_base_version="kb-v1",
        retrieval_strategy_version="strategy-a",
        model_version="model-x",
        request_hash="req-123",
    )

    assert build_cache_key("rag:retrieval", base) != build_cache_key(
        "rag:retrieval",
        CacheKeyContext(
            user_identity="user-2",
            permission_scope=base.permission_scope,
            workspace_id=base.workspace_id,
            knowledge_base_version=base.knowledge_base_version,
            retrieval_strategy_version=base.retrieval_strategy_version,
            model_version=base.model_version,
            request_hash=base.request_hash,
        ),
    )
    assert build_cache_key("rag:retrieval", base) != build_cache_key(
        "rag:retrieval",
        CacheKeyContext(
            user_identity=base.user_identity,
            permission_scope=base.permission_scope,
            workspace_id="workspace-b",
            knowledge_base_version=base.knowledge_base_version,
            retrieval_strategy_version=base.retrieval_strategy_version,
            model_version=base.model_version,
            request_hash=base.request_hash,
        ),
    )
    assert build_cache_key("rag:retrieval", base) != build_cache_key(
        "rag:retrieval",
        CacheKeyContext(
            user_identity=base.user_identity,
            permission_scope="admin",
            workspace_id=base.workspace_id,
            knowledge_base_version=base.knowledge_base_version,
            retrieval_strategy_version=base.retrieval_strategy_version,
            model_version=base.model_version,
            request_hash=base.request_hash,
        ),
    )
    assert build_cache_key("rag:retrieval", base) != build_cache_key(
        "rag:retrieval",
        CacheKeyContext(
            user_identity=base.user_identity,
            permission_scope=base.permission_scope,
            workspace_id=base.workspace_id,
            knowledge_base_version=base.knowledge_base_version,
            retrieval_strategy_version="strategy-b",
            model_version=base.model_version,
            request_hash=base.request_hash,
        ),
    )
    assert build_request_hash({"question": "What changed?"}) == build_request_hash({"question": "What changed?"})


def test_get_cache_adapter_uses_redis_when_configured_and_dependency_is_available(monkeypatch) -> None:
    fake_client = SimpleNamespace(
        ping_called=False,
        stored={},
        deleted=[],
        get=lambda key: fake_client.stored.get(key),
        set=lambda key, value: fake_client.stored.__setitem__(key, value),
        setex=lambda key, ttl, value: fake_client.stored.__setitem__(key, value),
        delete=lambda *keys: fake_client.deleted.extend(keys),
        keys=lambda pattern: [key for key in fake_client.stored if key.startswith(pattern[:-1])],
        ping=lambda: setattr(fake_client, "ping_called", True),
    )

    fake_redis_module = SimpleNamespace(from_url=lambda url, decode_responses: fake_client)
    monkeypatch.setattr("app.storage.cache.redis", fake_redis_module, raising=False)

    adapter = get_cache_adapter(SimpleNamespace(redis_url="redis://localhost:6379/0"))

    assert isinstance(adapter, RedisCacheAdapter)
    adapter.set("rag:query:key", {"ok": True}, ttl_seconds=15)
    assert fake_client.ping_called is True
    assert fake_client.stored["paiguangguang:cache:rag:query:key"] == "{\"ok\":true}"


def test_get_cache_adapter_falls_back_to_memory_when_redis_is_unavailable(monkeypatch) -> None:
    monkeypatch.setattr("app.storage.cache.redis", None, raising=False)

    adapter = get_cache_adapter(SimpleNamespace(redis_url="redis://localhost:6379/0"))

    assert isinstance(adapter, InMemoryCacheAdapter)
