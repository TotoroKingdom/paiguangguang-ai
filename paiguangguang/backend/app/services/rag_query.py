from __future__ import annotations

from dataclasses import asdict
from time import perf_counter

from app.ai.deepseek import DeepSeekClient, DeepSeekError
from app.ai.rerank import RerankProvider, get_rerank_provider
from app.core.config import get_settings
from app.db.models import User
from app.schemas.rag import (
    RagQueryData,
    RagQueryDebugData,
    RagQueryRequest,
    RagQueryRewriteData,
    RagSourceData,
)
from app.services.context_assembler import ContextAssembler, ContextAssemblyResult, get_context_assembler
from app.services.rag_cache import (
    RAG_KNOWLEDGE_BASE_VERSION,
    RAG_RETRIEVAL_STRATEGY_VERSION,
    build_authorized_cache_key,
    invalidate_document_cache,
    get_rag_cache_adapter,
    remember_document_cache_keys,
)
from app.storage.chroma_store import RagSearchAccessContext
from app.services.hybrid_retrieval import (
    HybridRetrievalHit,
    HybridRetrievalService,
    HybridRetrievalTrace,
    get_hybrid_retrieval_service,
)
from app.services.query_rewrite import QueryRewriteService, get_query_rewrite_service
from app.services.rbac import RBACService, get_rbac_service
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.models import Workspace, WorkspaceMembership
from fastapi import HTTPException, status


def build_rag_system_prompt() -> str:
    return (
        "You are the Knowledge Agent for the portfolio site.\n"
        "Answer only with the evidence from the retrieved context.\n"
        "If the context is insufficient, say so clearly.\n"
        "When helpful, mention source identifiers in the form [doc_id / chunk_id]."
    )
class RagQueryService:
    def __init__(
        self,
        retrieval_service: HybridRetrievalService | None = None,
        context_assembler: ContextAssembler | None = None,
        client: DeepSeekClient | None = None,
        rewrite_service: QueryRewriteService | None = None,
        rerank_provider: RerankProvider | None = None,
        cache_adapter=None,
    ) -> None:
        settings = get_settings()
        self.client = client or DeepSeekClient(settings)
        self.retrieval_service = retrieval_service or get_hybrid_retrieval_service()
        self.context_assembler = context_assembler or get_context_assembler()
        self.rewrite_service = rewrite_service or get_query_rewrite_service()
        self.rerank_provider = rerank_provider if rerank_provider is not None else get_rerank_provider(settings)
        self.cache_adapter = cache_adapter or get_rag_cache_adapter(settings)
        self.default_collection_name = settings.rag_collection_name
        self.knowledge_base_version = RAG_KNOWLEDGE_BASE_VERSION
        self.retrieval_strategy_version = RAG_RETRIEVAL_STRATEGY_VERSION
        self.answer_model_version = settings.deepseek_chat_model
        self.retrieval_model_version = ":".join(
            [
                self.rewrite_service.model,
                self.rerank_provider.__class__.__name__ if self.rerank_provider is not None else "none",
            ]
        )

    def query(
        self,
        request: RagQueryRequest,
        *,
        access_context: RagSearchAccessContext | None = None,
        cache_bypass: bool = False,
    ) -> RagQueryData:
        started_at = perf_counter()
        collection_name = request.collection or self.default_collection_name
        rewrite = self.rewrite_service.rewrite(request.question, cache_bypass=cache_bypass)
        trace = self._get_retrieval_trace(
            collection_name,
            request=request,
            rewrite=rewrite,
            access_context=access_context,
            cache_bypass=cache_bypass,
        )
        hits = trace.fusion_hits
        fusion_hits = list(hits)
        hits = self._apply_rerank(request.question, hits)
        assembly = self.context_assembler.assemble(hits)

        cached_result = self._load_answer_cache(
            request=request,
            rewrite=rewrite,
            access_context=access_context,
            assembly=assembly,
            cache_bypass=cache_bypass,
        )
        if cached_result is not None:
            debug = self._build_debug_data(
                request,
                rewrite=rewrite,
                trace=trace,
                fusion_hits=fusion_hits,
                reranked_hits=hits,
                assembly=assembly,
                latency_ms=int((perf_counter() - started_at) * 1000),
                model_usage={},
            )
            return RagQueryData(
                answer=cached_result.answer,
                sources=cached_result.sources,
                rewrite=rewrite,
                debug=debug,
            )

        answer, model_usage = self._ask_model(request.question, assembly)

        sources = [
            self._hit_to_source_data(hit)
            for hit in assembly.selected_sources
        ]
        debug = self._build_debug_data(
            request,
            rewrite=rewrite,
            trace=trace,
            fusion_hits=fusion_hits,
            reranked_hits=hits,
            assembly=assembly,
            latency_ms=int((perf_counter() - started_at) * 1000),
            model_usage=model_usage,
        )
        result = RagQueryData(answer=answer, sources=sources, rewrite=rewrite, debug=debug)
        self._store_answer_cache(
            request=request,
            rewrite=rewrite,
            access_context=access_context,
            assembly=assembly,
            result=result,
            cache_bypass=cache_bypass,
        )
        return result

    def query_for_user(
        self,
        request: RagQueryRequest,
        *,
        session: Session,
        user: User,
        rbac_service: RBACService | None = None,
        cache_bypass: bool = False,
    ) -> RagQueryData:
        rbac_service = rbac_service or get_rbac_service()
        if not rbac_service.has_permission(session, user.id, "knowledge.query"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="knowledge.query permission required",
            )

        access_context = self._build_access_context(session, user)
        return self.query(request, access_context=access_context, cache_bypass=cache_bypass)

    def _build_access_context(self, session: Session, user: User) -> RagSearchAccessContext:
        workspace_id = self._resolve_workspace_id(session, user)
        role_names = {role.name for role in user.roles}
        is_system_admin = "system_admin" in role_names
        allowed_scopes = ("workspace", "admin") if role_names & {"document_admin", "system_admin"} else ("workspace",)
        return RagSearchAccessContext(
            workspace_id=workspace_id,
            user_id=user.id,
            is_system_admin=is_system_admin,
            allowed_permission_scopes=allowed_scopes,
            allow_legacy_metadata=True,
        )

    @staticmethod
    def _resolve_workspace_id(session: Session, user: User) -> str | None:
        membership_workspace_id = session.scalar(
            select(WorkspaceMembership.workspace_id)
            .where(WorkspaceMembership.user_id == user.id)
            .order_by(WorkspaceMembership.created_at.asc())
        )
        if isinstance(membership_workspace_id, str) and membership_workspace_id.strip():
            return membership_workspace_id

        default_workspace_id = session.scalar(select(Workspace.id).where(Workspace.is_default.is_(True)))
        return default_workspace_id if isinstance(default_workspace_id, str) else None

    def _ask_model(self, question: str, assembly: ContextAssemblyResult) -> tuple[str, dict[str, object]]:
        messages = [
            {"role": "system", "content": build_rag_system_prompt()},
            {
                "role": "user",
                "content": (
                    f"Question:\n{question}\n\n"
                    f"Retrieved context:\n{assembly.context_text}\n\n"
                    "Write a concise answer grounded in the context. "
                    "If the context does not contain the answer, say that clearly."
                ),
            },
        ]

        result = self.client.chat_completions(messages)
        return self._extract_reply(result), self._extract_usage(result)

    def _get_retrieval_trace(
        self,
        collection_name: str,
        *,
        request: RagQueryRequest,
        rewrite: RagQueryRewriteData,
        access_context: RagSearchAccessContext | None,
        cache_bypass: bool,
    ) -> HybridRetrievalTrace:
        if access_context is None or request.include_debug or cache_bypass:
            return self.retrieval_service.search_with_trace(
                collection_name,
                rewrite.original_question,
                top_k=request.top_k,
                access_context=access_context,
                rewrite_queries=rewrite.rewritten_queries,
            )

        cache_key = build_authorized_cache_key(
            "rag:retrieval",
            access_context=access_context,
            knowledge_base_version=self.knowledge_base_version,
            retrieval_strategy_version=self.retrieval_strategy_version,
            model_version=self.retrieval_model_version,
            payload={
                "collection": collection_name,
                "question": request.question,
                "top_k": request.top_k,
                "rewrite": rewrite.model_dump(mode="json"),
            },
        )
        if cache_key is not None:
            cached = self.cache_adapter.get(cache_key)
            if isinstance(cached, dict):
                trace = self._trace_from_payload(cached)
                if trace is not None:
                    self._remember_trace_cache_keys(cache_key, trace)
                    return trace

        trace = self.retrieval_service.search_with_trace(
            collection_name,
            rewrite.original_question,
            top_k=request.top_k,
            access_context=access_context,
            rewrite_queries=rewrite.rewritten_queries,
        )
        if cache_key is not None:
            self.cache_adapter.set(cache_key, self._trace_to_payload(trace))
            self._remember_trace_cache_keys(cache_key, trace)
        return trace

    def _apply_rerank(self, question: str, hits: list[HybridRetrievalHit]) -> list[HybridRetrievalHit]:
        if self.rerank_provider is None or not hits:
            return hits

        rerank_results = self.rerank_provider.rerank(question, [hit.text for hit in hits], top_n=len(hits))
        if not rerank_results:
            return hits

        reranked_hits: list[HybridRetrievalHit] = []
        seen_indexes: set[int] = set()
        for result in rerank_results:
            if result.index < 0 or result.index >= len(hits) or result.index in seen_indexes:
                continue
            seen_indexes.add(result.index)
            hit = hits[result.index]
            hit.rerank_score = result.relevance_score
            reranked_hits.append(hit)

        for index, hit in enumerate(hits):
            if index not in seen_indexes:
                hit.rerank_score = None
                reranked_hits.append(hit)

        return reranked_hits

    @staticmethod
    def _hit_to_source_data(hit: HybridRetrievalHit) -> RagSourceData:
        return RagSourceData(
            doc_id=hit.doc_id,
            chunk_id=hit.chunk_id,
            title=hit.title,
            page_number=hit.page_number,
            chunk_index=hit.chunk_index,
            text=hit.text,
            score=hit.score,
            rerank_score=hit.rerank_score,
            route_scores=dict(hit.route_scores),
            metadata=dict(hit.metadata),
        )

    @staticmethod
    def _hit_to_payload(hit: HybridRetrievalHit) -> dict[str, object]:
        return asdict(hit)

    @staticmethod
    def _hit_from_payload(payload: dict[str, object]) -> HybridRetrievalHit | None:
        try:
            return HybridRetrievalHit(
                doc_id=str(payload["doc_id"]),
                chunk_id=str(payload["chunk_id"]),
                title=payload.get("title") if payload.get("title") is None or isinstance(payload.get("title"), str) else None,
                page_number=payload.get("page_number") if payload.get("page_number") is None or isinstance(payload.get("page_number"), int) else None,
                chunk_index=int(payload.get("chunk_index", 0)),
                text=str(payload.get("text", "")),
                score=float(payload.get("score", 0.0)),
                start_char=int(payload.get("start_char", 0)),
                end_char=int(payload.get("end_char", 0)),
                metadata=dict(payload.get("metadata", {}) or {}),
                rerank_score=payload.get("rerank_score") if payload.get("rerank_score") is None or isinstance(payload.get("rerank_score"), (int, float)) else None,
                route_scores={str(key): float(value) for key, value in dict(payload.get("route_scores", {}) or {}).items()},
            )
        except Exception:
            return None

    def _trace_to_payload(self, trace: HybridRetrievalTrace) -> dict[str, object]:
        return {
            "queries": list(trace.queries),
            "vector_hits": [self._hit_to_payload(hit) for hit in trace.vector_hits],
            "keyword_hits": [self._hit_to_payload(hit) for hit in trace.keyword_hits],
            "fusion_hits": [self._hit_to_payload(hit) for hit in trace.fusion_hits],
        }

    def _trace_from_payload(self, payload: dict[str, object]) -> HybridRetrievalTrace | None:
        queries = payload.get("queries")
        vector_hits_payload = payload.get("vector_hits")
        keyword_hits_payload = payload.get("keyword_hits")
        fusion_hits_payload = payload.get("fusion_hits")
        if not isinstance(queries, list) or not isinstance(vector_hits_payload, list) or not isinstance(keyword_hits_payload, list) or not isinstance(fusion_hits_payload, list):
            return None

        vector_hits = [
            hit
            for item in vector_hits_payload
            if isinstance(item, dict) and (hit := self._hit_from_payload(item)) is not None
        ]
        keyword_hits = [
            hit
            for item in keyword_hits_payload
            if isinstance(item, dict) and (hit := self._hit_from_payload(item)) is not None
        ]
        fusion_hits = [
            hit
            for item in fusion_hits_payload
            if isinstance(item, dict) and (hit := self._hit_from_payload(item)) is not None
        ]
        return HybridRetrievalTrace(
            queries=[str(query) for query in queries if isinstance(query, str)],
            vector_hits=vector_hits,
            keyword_hits=keyword_hits,
            fusion_hits=fusion_hits,
        )

    def _load_answer_cache(
        self,
        *,
        request: RagQueryRequest,
        rewrite: RagQueryRewriteData,
        access_context: RagSearchAccessContext | None,
        assembly: ContextAssemblyResult,
        cache_bypass: bool,
    ) -> RagQueryData | None:
        if access_context is None or request.include_debug or cache_bypass:
            return None

        cache_key = build_authorized_cache_key(
            "rag:answer",
            access_context=access_context,
            knowledge_base_version=self.knowledge_base_version,
            retrieval_strategy_version=self.retrieval_strategy_version,
            model_version=self.answer_model_version,
            payload={
                "question": request.question,
                "collection": request.collection or self.default_collection_name,
                "top_k": request.top_k,
                "rewrite": rewrite.model_dump(mode="json"),
                "selected_sources": [self._hit_to_payload(source) for source in assembly.selected_sources],
                "context_text": assembly.context_text,
            },
        )
        if cache_key is None:
            return None

        cached = self.cache_adapter.get(cache_key)
        if isinstance(cached, dict):
            try:
                return RagQueryData.model_validate(cached)
            except Exception:
                return None
        return None

    def _store_answer_cache(
        self,
        *,
        request: RagQueryRequest,
        rewrite: RagQueryRewriteData,
        access_context: RagSearchAccessContext | None,
        assembly: ContextAssemblyResult,
        result: RagQueryData,
        cache_bypass: bool,
    ) -> None:
        if access_context is None or request.include_debug or cache_bypass:
            return

        cache_key = build_authorized_cache_key(
            "rag:answer",
            access_context=access_context,
            knowledge_base_version=self.knowledge_base_version,
            retrieval_strategy_version=self.retrieval_strategy_version,
            model_version=self.answer_model_version,
            payload={
                "question": request.question,
                "collection": request.collection or self.default_collection_name,
                "top_k": request.top_k,
                "rewrite": rewrite.model_dump(mode="json"),
                "selected_sources": [self._hit_to_payload(source) for source in assembly.selected_sources],
                "context_text": assembly.context_text,
            },
        )
        if cache_key is not None:
            self.cache_adapter.set(cache_key, result.model_dump(mode="json"))
            self._remember_answer_cache_keys(cache_key, result)

    def purge_document_cache(self, document_id: str) -> None:
        invalidate_document_cache(self.cache_adapter, document_id)

    def _build_debug_data(
        self,
        request: RagQueryRequest,
        *,
        rewrite: RagQueryRewriteData | None,
        trace: HybridRetrievalTrace,
        fusion_hits: list[HybridRetrievalHit],
        reranked_hits: list[HybridRetrievalHit],
        assembly: ContextAssemblyResult,
        latency_ms: int,
        model_usage: dict[str, object],
    ) -> RagQueryDebugData | None:
        if not request.include_debug:
            return None

        return RagQueryDebugData(
            rewrites=rewrite,
            vector_hits=[self._hit_to_source_data(hit) for hit in trace.vector_hits],
            keyword_hits=[self._hit_to_source_data(hit) for hit in trace.keyword_hits],
            fusion=[self._hit_to_source_data(hit) for hit in fusion_hits],
            rerank=[self._hit_to_source_data(hit) for hit in reranked_hits],
            selected_context=[self._hit_to_source_data(hit) for hit in assembly.selected_sources],
            citations=[self._hit_to_source_data(hit) for hit in assembly.selected_sources],
            latency_ms=latency_ms,
            model_usage=dict(model_usage),
        )

    def _remember_trace_cache_keys(self, cache_key: str, trace: HybridRetrievalTrace) -> None:
        document_ids = {hit.doc_id for hit in (*trace.vector_hits, *trace.keyword_hits, *trace.fusion_hits)}
        for document_id in document_ids:
            remember_document_cache_keys(self.cache_adapter, document_id, [cache_key])

    def _remember_answer_cache_keys(self, cache_key: str, result: RagQueryData) -> None:
        document_ids = {source.doc_id for source in result.sources}
        for document_id in document_ids:
            remember_document_cache_keys(self.cache_adapter, document_id, [cache_key])

    @staticmethod
    def _extract_reply(payload: dict[str, object]) -> str:
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise DeepSeekError("DeepSeek returned no choices")

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise DeepSeekError("DeepSeek returned an invalid choice payload")

        message = first_choice.get("message")
        if not isinstance(message, dict):
            raise DeepSeekError("DeepSeek returned an invalid message payload")

        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise DeepSeekError("DeepSeek returned an empty reply")

        return content.strip()

    @staticmethod
    def _extract_usage(payload: dict[str, object]) -> dict[str, object]:
        usage = payload.get("usage")
        if isinstance(usage, dict):
            result = dict(usage)
            model = payload.get("model")
            if isinstance(model, str) and model.strip():
                result.setdefault("model", model.strip())
            return result
        model = payload.get("model")
        if isinstance(model, str) and model.strip():
            return {"model": model.strip()}
        return {}


_RAG_QUERY_SERVICE = RagQueryService()


def get_rag_query_service() -> RagQueryService:
    return _RAG_QUERY_SERVICE
