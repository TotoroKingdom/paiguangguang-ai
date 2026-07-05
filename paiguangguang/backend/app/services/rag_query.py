from __future__ import annotations

from app.ai.deepseek import DeepSeekClient, DeepSeekError
from app.ai.rerank import RerankProvider, get_rerank_provider
from app.core.config import get_settings
from app.db.models import User
from app.schemas.rag import RagQueryData, RagQueryRequest, RagSourceData
from app.services.context_assembler import ContextAssembler, ContextAssemblyResult, get_context_assembler
from app.storage.chroma_store import RagSearchAccessContext
from app.services.hybrid_retrieval import HybridRetrievalHit, HybridRetrievalService, get_hybrid_retrieval_service
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
    ) -> None:
        settings = get_settings()
        self.client = client or DeepSeekClient(settings)
        self.retrieval_service = retrieval_service or get_hybrid_retrieval_service()
        self.context_assembler = context_assembler or get_context_assembler()
        self.rewrite_service = rewrite_service or get_query_rewrite_service()
        self.rerank_provider = rerank_provider if rerank_provider is not None else get_rerank_provider(settings)
        self.default_collection_name = settings.rag_collection_name

    def query(
        self,
        request: RagQueryRequest,
        *,
        access_context: RagSearchAccessContext | None = None,
    ) -> RagQueryData:
        collection_name = request.collection or self.default_collection_name
        rewrite = self.rewrite_service.rewrite(request.question)
        hits = self.retrieval_service.search(
            collection_name,
            rewrite.original_question,
            top_k=request.top_k,
            access_context=access_context,
            rewrite_queries=rewrite.rewritten_queries,
        )
        hits = self._apply_rerank(request.question, hits)
        assembly = self.context_assembler.assemble(hits)

        sources = [
            RagSourceData(
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
            for hit in assembly.selected_sources
        ]
        answer = self._ask_model(request.question, assembly)
        return RagQueryData(answer=answer, sources=sources, rewrite=rewrite)

    def query_for_user(
        self,
        request: RagQueryRequest,
        *,
        session: Session,
        user: User,
        rbac_service: RBACService | None = None,
    ) -> RagQueryData:
        rbac_service = rbac_service or get_rbac_service()
        if not rbac_service.has_permission(session, user.id, "knowledge.query"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="knowledge.query permission required",
            )

        access_context = self._build_access_context(session, user)
        return self.query(request, access_context=access_context)

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

    def _ask_model(self, question: str, assembly: ContextAssemblyResult) -> str:
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
        return self._extract_reply(result)

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


_RAG_QUERY_SERVICE = RagQueryService()


def get_rag_query_service() -> RagQueryService:
    return _RAG_QUERY_SERVICE
