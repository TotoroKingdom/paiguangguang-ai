from __future__ import annotations

from types import SimpleNamespace

from app.services.hybrid_retrieval import HybridRetrievalService
from app.storage.chroma_store import RagSearchAccessContext


class QueryAwareFakeSearchStore:
    def __init__(self, responses):
        self.responses = {key: list(value) for key, value in responses.items()}
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
        hits = list(self.responses.get(query_text, []))
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


def _make_hit(
    doc_id: str,
    chunk_id: str,
    *,
    score: float,
    text: str,
    workspace_id: str = "workspace-1",
    permission_scope: str = "workspace",
):
    return SimpleNamespace(
        doc_id=doc_id,
        chunk_id=chunk_id,
        title=f"Title {doc_id}",
        page_number=1,
        chunk_index=0,
        text=text,
        score=score,
        start_char=0,
        end_char=len(text),
        metadata={
            "doc_id": doc_id,
            "chunk_id": chunk_id,
            "title": f"Title {doc_id}",
            "page_number": 1,
            "chunk_index": 0,
            "workspace_id": workspace_id,
            "permission_scope": permission_scope,
            "start_char": 0,
            "end_char": len(text),
        },
    )


def test_hybrid_retrieval_merges_duplicate_candidates_and_is_stable() -> None:
    duplicate_hit = _make_hit("doc-alpha", "doc-alpha-chunk-0000", score=0.91, text="Alpha deployment notes")
    vector_store = QueryAwareFakeSearchStore({"alpha": [duplicate_hit]})
    keyword_retriever = QueryAwareFakeSearchStore({"alpha": [duplicate_hit]})
    service = HybridRetrievalService(vector_store=vector_store, keyword_retriever=keyword_retriever)
    access_context = RagSearchAccessContext(workspace_id="workspace-1", allowed_permission_scopes=("workspace",))

    first = service.search("portfolio_knowledge", "alpha", top_k=5, access_context=access_context)
    second = service.search("portfolio_knowledge", "alpha", top_k=5, access_context=access_context)

    assert len(first) == 1
    assert first[0].doc_id == "doc-alpha"
    assert first[0].chunk_id == "doc-alpha-chunk-0000"
    assert first[0].route_scores == {"vector": 0.91, "keyword": 0.91}
    assert first[0].score == second[0].score
    assert [(hit.doc_id, hit.chunk_id, hit.score) for hit in first] == [
        (hit.doc_id, hit.chunk_id, hit.score) for hit in second
    ]


def test_hybrid_retrieval_keeps_vector_only_and_keyword_only_candidates() -> None:
    vector_only_hit = _make_hit("doc-vector", "doc-vector-chunk-0000", score=0.87, text="Vector search only")
    keyword_only_hit = _make_hit("doc-keyword", "doc-keyword-chunk-0000", score=0.88, text="Keyword search only")
    vector_store = QueryAwareFakeSearchStore({"alpha": [vector_only_hit], "beta": []})
    keyword_retriever = QueryAwareFakeSearchStore({"alpha": [], "beta": [keyword_only_hit]})
    service = HybridRetrievalService(vector_store=vector_store, keyword_retriever=keyword_retriever)
    access_context = RagSearchAccessContext(workspace_id="workspace-1", allowed_permission_scopes=("workspace",))

    hits = service.search(
        "portfolio_knowledge",
        "alpha",
        top_k=5,
        access_context=access_context,
        rewrite_queries=("beta",),
    )

    assert [(hit.doc_id, hit.chunk_id) for hit in hits] == [
        ("doc-keyword", "doc-keyword-chunk-0000"),
        ("doc-vector", "doc-vector-chunk-0000"),
    ]
    assert hits[0].route_scores == {"keyword": 0.88}
    assert hits[1].route_scores == {"vector": 0.87}
