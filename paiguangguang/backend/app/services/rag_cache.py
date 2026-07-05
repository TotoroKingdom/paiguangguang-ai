from __future__ import annotations

from typing import Any

from app.core.config import Settings, get_settings
from app.storage.cache import CacheAdapter, CacheKeyContext, build_cache_key, build_request_hash
from app.storage.rag_search import RagSearchAccessContext


RAG_KNOWLEDGE_BASE_VERSION = "portfolio-knowledge-base"
RAG_RETRIEVAL_STRATEGY_VERSION = "rewrite-hybrid-rerank-v1"
RAG_EMBEDDING_STRATEGY_VERSION = "embedding-v1"


def get_rag_cache_adapter(settings: Settings | None = None) -> CacheAdapter:
    from app.storage.cache import get_cache_adapter

    return get_cache_adapter(settings or get_settings())


def build_shared_cache_key(namespace: str, *, model_version: str, payload: Any) -> str:
    return build_cache_key(
        namespace,
        CacheKeyContext(
            user_identity="shared",
            permission_scope="shared",
            workspace_id="shared",
            knowledge_base_version=RAG_KNOWLEDGE_BASE_VERSION,
            retrieval_strategy_version=RAG_RETRIEVAL_STRATEGY_VERSION,
            model_version=model_version,
            request_hash=build_request_hash(payload),
        ),
    )


def build_authorized_cache_key(
    namespace: str,
    *,
    access_context: RagSearchAccessContext | None,
    knowledge_base_version: str,
    retrieval_strategy_version: str,
    model_version: str,
    payload: Any,
) -> str | None:
    if access_context is None:
        return None

    permission_scope = ",".join(access_context.allowed_permission_scopes) if access_context.allowed_permission_scopes else "none"
    return build_cache_key(
        namespace,
        CacheKeyContext(
            user_identity=str(access_context.user_id or "anonymous"),
            permission_scope=permission_scope,
            workspace_id=str(access_context.workspace_id or "none"),
            knowledge_base_version=knowledge_base_version,
            retrieval_strategy_version=retrieval_strategy_version,
            model_version=model_version,
            request_hash=build_request_hash(payload),
        ),
    )
