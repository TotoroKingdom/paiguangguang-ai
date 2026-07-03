from __future__ import annotations

from app.ai.deepseek import DeepSeekClient, DeepSeekError
from app.core.config import get_settings
from app.schemas.rag import RagQueryData, RagQueryRequest, RagSourceData
from app.storage.chroma_store import ChromaRagStore, RagSearchHit, get_chroma_rag_store


def build_rag_system_prompt() -> str:
    return (
        "You are the Knowledge Agent for the portfolio site.\n"
        "Answer only with the evidence from the retrieved context.\n"
        "If the context is insufficient, say so clearly.\n"
        "When helpful, mention source identifiers in the form [doc_id / chunk_id]."
    )


def build_context_block(hits: list[RagSearchHit]) -> str:
    if not hits:
        return "No relevant context was retrieved."

    lines: list[str] = []
    for index, hit in enumerate(hits, start=1):
        title = f" | title={hit.title}" if hit.title else ""
        lines.append(
            f"[{index}] doc_id={hit.doc_id} | chunk_id={hit.chunk_id} | score={hit.score:.4f}{title}\n"
            f"{hit.text}"
        )
    return "\n\n".join(lines)


class RagQueryService:
    def __init__(
        self,
        vector_store: ChromaRagStore | None = None,
        client: DeepSeekClient | None = None,
    ) -> None:
        settings = get_settings()
        self.vector_store = vector_store or get_chroma_rag_store()
        self.client = client or DeepSeekClient(settings)
        self.default_collection_name = settings.rag_collection_name

    def query(self, request: RagQueryRequest) -> RagQueryData:
        collection_name = request.collection or self.default_collection_name
        hits = self.vector_store.search(
            collection_name,
            request.question,
            top_k=request.top_k,
        )

        sources = [
            RagSourceData(
                doc_id=hit.doc_id,
                chunk_id=hit.chunk_id,
                text=hit.text,
                score=hit.score,
            )
            for hit in hits
        ]
        answer = self._ask_model(request.question, hits)
        return RagQueryData(answer=answer, sources=sources)

    def _ask_model(self, question: str, hits: list[RagSearchHit]) -> str:
        context_block = build_context_block(hits)
        messages = [
            {"role": "system", "content": build_rag_system_prompt()},
            {
                "role": "user",
                "content": (
                    f"Question:\n{question}\n\n"
                    f"Retrieved context:\n{context_block}\n\n"
                    "Write a concise answer grounded in the context. "
                    "If the context does not contain the answer, say that clearly."
                ),
            },
        ]

        result = self.client.chat_completions(messages)
        return self._extract_reply(result)

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
