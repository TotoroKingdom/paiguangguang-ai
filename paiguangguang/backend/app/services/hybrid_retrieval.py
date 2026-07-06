from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from app.storage.chroma_store import ChromaRagStore, RagSearchAccessContext, RagSearchHit, get_chroma_rag_store
from app.storage.keyword_retriever import KeywordRetriever, get_keyword_retriever


@dataclass
class HybridRetrievalHit:
    doc_id: str
    chunk_id: str
    title: str | None
    page_number: int | None
    chunk_index: int
    text: str
    score: float
    start_char: int
    end_char: int
    metadata: dict[str, object]
    rerank_score: float | None = None
    route_scores: dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_search_hit(cls, hit: RagSearchHit, *, route_name: str) -> "HybridRetrievalHit":
        return cls(
            doc_id=hit.doc_id,
            chunk_id=hit.chunk_id,
            title=hit.title,
            page_number=hit.page_number,
            chunk_index=hit.chunk_index,
            text=hit.text,
            score=0.0,
            rerank_score=None,
            start_char=hit.start_char,
            end_char=hit.end_char,
            metadata=dict(hit.metadata),
            route_scores={route_name: hit.score},
        )

    def merge_search_hit(self, hit: RagSearchHit, *, route_name: str) -> None:
        self.metadata.update(hit.metadata)
        self.route_scores[route_name] = max(self.route_scores.get(route_name, 0.0), hit.score)
        if not self.title and hit.title:
            self.title = hit.title
        if self.page_number is None and hit.page_number is not None:
            self.page_number = hit.page_number
        self.chunk_index = min(self.chunk_index, hit.chunk_index)
        self.start_char = min(self.start_char, hit.start_char)
        self.end_char = max(self.end_char, hit.end_char)


@dataclass(frozen=True)
class HybridRetrievalTrace:
    queries: list[str]
    vector_hits: list[HybridRetrievalHit]
    keyword_hits: list[HybridRetrievalHit]
    direct_hits: list[HybridRetrievalHit]
    fusion_hits: list[HybridRetrievalHit]


class HybridRetrievalService:
    def __init__(
        self,
        vector_store: ChromaRagStore | None = None,
        keyword_retriever: KeywordRetriever | None = None,
        *,
        rrf_k: float = 60.0,
    ) -> None:
        self.vector_store = vector_store or get_chroma_rag_store()
        self.keyword_retriever = keyword_retriever or get_keyword_retriever()
        self.rrf_k = rrf_k

    def search(
        self,
        collection_name: str,
        query_text: str,
        *,
        top_k: int = 5,
        access_context: RagSearchAccessContext | None = None,
        rewrite_queries: Sequence[str] = (),
    ) -> list[HybridRetrievalHit]:
        return self.search_with_trace(
            collection_name,
            query_text,
            top_k=top_k,
            access_context=access_context,
            rewrite_queries=rewrite_queries,
        ).fusion_hits

    def search_with_trace(
        self,
        collection_name: str,
        query_text: str,
        *,
        top_k: int = 5,
        access_context: RagSearchAccessContext | None = None,
        rewrite_queries: Sequence[str] = (),
    ) -> HybridRetrievalTrace:
        queries = self._build_queries(query_text, rewrite_queries)
        if not queries:
            return HybridRetrievalTrace(queries=[], vector_hits=[], keyword_hits=[], direct_hits=[], fusion_hits=[])

        candidates: dict[tuple[str, str], HybridRetrievalHit] = {}
        vector_hits: list[HybridRetrievalHit] = []
        keyword_hits: list[HybridRetrievalHit] = []
        direct_hits: list[HybridRetrievalHit] = []
        for query in queries:
            vector_route_hits = self.vector_store.search(
                collection_name,
                query,
                top_k=top_k,
                access_context=access_context,
            )
            keyword_route_hits = self.keyword_retriever.search(
                collection_name,
                query,
                top_k=top_k,
                access_context=access_context,
            )
            direct_search = getattr(self.keyword_retriever, "search_direct_match", None)
            if callable(direct_search):
                direct_route_hits = direct_search(
                    collection_name,
                    query,
                    top_k=top_k,
                    access_context=access_context,
                )
            else:
                direct_route_hits = keyword_route_hits
            vector_hits.extend(self._clone_hit(hit, "vector") for hit in vector_route_hits)
            keyword_hits.extend(self._clone_hit(hit, "bm25") for hit in keyword_route_hits)
            direct_hits.extend(self._clone_hit(hit, "direct") for hit in direct_route_hits)
            self._merge_route_hits(
                candidates,
                "vector",
                vector_route_hits,
            )
            self._merge_route_hits(
                candidates,
                "bm25",
                keyword_route_hits,
            )
            self._merge_route_hits(
                candidates,
                "direct",
                direct_route_hits,
            )

        fusion_hits = sorted(
            candidates.values(),
            key=lambda hit: (-hit.score, hit.doc_id, hit.chunk_id),
        )[:top_k]
        return HybridRetrievalTrace(
            queries=queries,
            vector_hits=vector_hits,
            keyword_hits=keyword_hits,
            direct_hits=direct_hits,
            fusion_hits=fusion_hits,
        )

    def _merge_route_hits(
        self,
        candidates: dict[tuple[str, str], HybridRetrievalHit],
        route_name: str,
        hits: Sequence[RagSearchHit],
    ) -> None:
        for rank, hit in enumerate(hits, start=1):
            key = (hit.doc_id, hit.chunk_id)
            candidate = candidates.get(key)
            if candidate is None:
                candidate = HybridRetrievalHit.from_search_hit(hit, route_name=route_name)
                candidates[key] = candidate
            else:
                candidate.merge_search_hit(hit, route_name=route_name)
            candidate.score += 1.0 / (self.rrf_k + rank)

    @staticmethod
    def _clone_hit(hit: RagSearchHit, route_name: str) -> HybridRetrievalHit:
        cloned = HybridRetrievalHit.from_search_hit(hit, route_name=route_name)
        cloned.score = hit.score
        return cloned

    @staticmethod
    def _build_queries(query_text: str, rewrite_queries: Sequence[str]) -> list[str]:
        queries: list[str] = []
        seen: set[str] = set()
        for candidate in (query_text, *rewrite_queries):
            normalized = candidate.strip()
            if not normalized:
                continue
            key = normalized.casefold()
            if key in seen:
                continue
            seen.add(key)
            queries.append(normalized)
        return queries


_HYBRID_RETRIEVAL_SERVICE = HybridRetrievalService()


def get_hybrid_retrieval_service() -> HybridRetrievalService:
    return _HYBRID_RETRIEVAL_SERVICE
