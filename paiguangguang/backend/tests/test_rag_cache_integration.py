from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import httpx

from app.ai.deepseek import DeepSeekClient
from app.ai.embeddings import CachingEmbeddingProvider
from app.schemas.rag import RagQueryRequest
from app.services.context_assembler import ContextAssemblyResult
from app.services.hybrid_retrieval import HybridRetrievalHit, HybridRetrievalService
from app.services.query_rewrite import QueryRewriteService
from app.services.rag_query import RagQueryService
from app.storage.cache import InMemoryCacheAdapter
from app.storage.rag_search import RagSearchAccessContext


class FakeSearchStore:
    def __init__(self, hits):
        self.hits = list(hits)
        self.calls: list[dict[str, object]] = []

    def search(self, collection_name, query_text, *, top_k=5, access_context=None):
        self.calls.append(
            {
                "collection_name": collection_name,
                "query_text": query_text,
                "top_k": top_k,
                "access_context": access_context,
            }
        )
        hits = list(self.hits)
        if access_context is not None:
            filtered = []
            for hit in hits:
                metadata = getattr(hit, "metadata", {}) or {}
                if access_context.is_system_admin:
                    filtered.append(hit)
                    continue
                workspace_id = metadata.get("workspace_id")
                permission_scope = metadata.get("permission_scope")
                if workspace_id is None or permission_scope is None:
                    if access_context.allow_legacy_metadata:
                        filtered.append(hit)
                    continue
                if access_context.workspace_id is not None and workspace_id != access_context.workspace_id:
                    continue
                if permission_scope in access_context.allowed_permission_scopes:
                    filtered.append(hit)
            hits = filtered
        return hits[:top_k]


class FakeContextAssembler:
    def __init__(self, result: ContextAssemblyResult | None = None) -> None:
        self.result = result
        self.calls: list[list[HybridRetrievalHit]] = []

    def assemble(self, hits):
        self.calls.append(list(hits))
        if self.result is not None:
            return self.result
        context_text = "\n\n".join(
            f"[{index}] doc_id={hit.doc_id} | chunk_id={hit.chunk_id}\n{hit.text}"
            for index, hit in enumerate(hits, start=1)
        )
        return ContextAssemblyResult(
            context_text=context_text or "No relevant context was retrieved.",
            selected_sources=list(hits),
            total_characters=len(context_text),
            truncated=False,
        )


@dataclass
class CountingEmbeddingProvider:
    dimension: int = 3
    calls: int = 0

    def embed(self, texts):
        self.calls += 1
        vectors = []
        for text in texts:
            lowered = text.lower()
            vectors.append(
                [
                    1.0 if "alpha" in lowered else 0.0,
                    1.0 if "beta" in lowered else 0.0,
                    1.0 if "gamma" in lowered else 0.0,
                ]
            )
        return vectors


def _make_hit(*, doc_id: str, chunk_id: str, text: str, score: float, workspace_id: str, permission_scope: str):
    return SimpleNamespace(
        doc_id=doc_id,
        chunk_id=chunk_id,
        title=f"Title for {doc_id}",
        page_number=1,
        chunk_index=1,
        text=text,
        score=score,
        start_char=0,
        end_char=len(text),
        metadata={
            "doc_id": doc_id,
            "chunk_id": chunk_id,
            "title": f"Title for {doc_id}",
            "page_number": 1,
            "chunk_index": 1,
            "workspace_id": workspace_id,
            "permission_scope": permission_scope,
            "start_char": 0,
            "end_char": len(text),
        },
    )


def test_embedding_cache_reuses_cached_vectors_and_supports_bypass() -> None:
    cache = InMemoryCacheAdapter()
    provider = CountingEmbeddingProvider()
    cached_provider = CachingEmbeddingProvider(provider=provider, cache_adapter=cache, model_version="embedding-v1")

    first = cached_provider.embed(["Alpha beta"])
    second = cached_provider.embed(["Alpha beta"])
    cached_provider.cache_bypass = True
    third = cached_provider.embed(["Alpha beta"])

    assert first == second == third
    assert provider.calls == 2


def test_query_rewrite_cache_reuses_model_output_and_supports_bypass() -> None:
    cache = InMemoryCacheAdapter()
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": '{"original_question":"How is the project deployed?","rewritten_queries":["deployment workflow"]}',
                        }
                    }
                ]
            },
        )

    service = QueryRewriteService(
        client=DeepSeekClient(api_key="test-key", transport=httpx.MockTransport(handler)),
        enabled=True,
        cache_adapter=cache,
    )

    first = service.rewrite("How is the project deployed?")
    second = service.rewrite("How is the project deployed?")
    third = service.rewrite("How is the project deployed?", cache_bypass=True)

    assert first == second
    assert first.original_question == "How is the project deployed?"
    assert first.rewritten_queries == ["deployment workflow"]
    assert len(requests) == 2
    assert third.rewritten_queries == ["deployment workflow"]


def test_rag_query_pipeline_uses_cached_retrieval_and_answer_results() -> None:
    cache = InMemoryCacheAdapter()
    captured_bodies: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_bodies.append(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "Use the retrieved context to answer the question.",
                        }
                    }
                ]
            },
        )

    accessible_hit = _make_hit(
        doc_id="doc-alpha",
        chunk_id="doc-alpha-chunk-0001",
        text="Alpha project deployment notes.",
        score=0.9,
        workspace_id="workspace-1",
        permission_scope="workspace",
    )
    vector_store = FakeSearchStore([accessible_hit])
    keyword_retriever = FakeSearchStore([accessible_hit])
    retrieval_service = HybridRetrievalService(vector_store=vector_store, keyword_retriever=keyword_retriever)
    context_assembler = FakeContextAssembler()
    rewrite_service = QueryRewriteService(enabled=False, cache_adapter=cache)
    query_service = RagQueryService(
        retrieval_service=retrieval_service,
        context_assembler=context_assembler,
        client=DeepSeekClient(api_key="test-key", transport=httpx.MockTransport(handler)),
        rewrite_service=rewrite_service,
        cache_adapter=cache,
    )

    access_context = RagSearchAccessContext(
        workspace_id="workspace-1",
        user_id="user-1",
        allowed_permission_scopes=("workspace",),
        allow_legacy_metadata=True,
    )
    request = RagQueryRequest(
        question="How is the project deployed?",
        collection="portfolio_knowledge",
        top_k=1,
    )

    first = query_service.query(request, access_context=access_context)
    second = query_service.query(request, access_context=access_context)
    bypassed = query_service.query(request, access_context=access_context, cache_bypass=True)

    assert first.answer == "Use the retrieved context to answer the question."
    assert second.answer == first.answer
    assert bypassed.answer == first.answer
    assert first.sources == second.sources
    assert len(captured_bodies) == 2
    assert len(vector_store.calls) == 2
    assert len(keyword_retriever.calls) == 2
    assert len(context_assembler.calls) == 3


def test_rag_query_cache_isolated_by_access_context() -> None:
    cache = InMemoryCacheAdapter()
    captured_bodies: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_bodies.append(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "Context is scoped by workspace and user.",
                        }
                    }
                ]
            },
        )

    accessible_hit = _make_hit(
        doc_id="doc-alpha",
        chunk_id="doc-alpha-chunk-0001",
        text="Alpha project deployment notes.",
        score=0.9,
        workspace_id="workspace-1",
        permission_scope="workspace",
    )
    vector_store = FakeSearchStore([accessible_hit])
    keyword_retriever = FakeSearchStore([accessible_hit])
    retrieval_service = HybridRetrievalService(vector_store=vector_store, keyword_retriever=keyword_retriever)
    query_service = RagQueryService(
        retrieval_service=retrieval_service,
        context_assembler=FakeContextAssembler(),
        client=DeepSeekClient(api_key="test-key", transport=httpx.MockTransport(handler)),
        rewrite_service=QueryRewriteService(enabled=False, cache_adapter=cache),
        cache_adapter=cache,
    )

    request = RagQueryRequest(
        question="How is the project deployed?",
        collection="portfolio_knowledge",
        top_k=1,
    )

    first_context = RagSearchAccessContext(
        workspace_id="workspace-1",
        user_id="user-1",
        allowed_permission_scopes=("workspace",),
        allow_legacy_metadata=True,
    )
    second_context = RagSearchAccessContext(
        workspace_id="workspace-2",
        user_id="user-2",
        allowed_permission_scopes=("workspace",),
        allow_legacy_metadata=True,
    )

    first = query_service.query(request, access_context=first_context)
    second = query_service.query(request, access_context=second_context)

    assert first.answer == "Context is scoped by workspace and user."
    assert second.answer == "Context is scoped by workspace and user."
    assert len(captured_bodies) == 2
    assert len(vector_store.calls) == 2
    assert len(keyword_retriever.calls) == 2
