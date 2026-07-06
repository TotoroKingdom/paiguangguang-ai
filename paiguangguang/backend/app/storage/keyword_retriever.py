from __future__ import annotations

from app.storage.rag_documents import RagDocumentRepository, get_rag_document_repository
from app.storage.rag_search import RagSearchAccessContext, RagSearchHit


class KeywordRetriever:
    def __init__(self, repository: RagDocumentRepository | None = None) -> None:
        self.repository = repository or get_rag_document_repository()

    def search(
        self,
        collection_name: str,
        query_text: str,
        *,
        top_k: int = 5,
        access_context: RagSearchAccessContext | None = None,
    ) -> list[RagSearchHit]:
        return self.repository.search_keyword(
            collection_name,
            query_text,
            top_k=top_k,
            access_context=access_context,
        )

    def search_direct_match(
        self,
        collection_name: str,
        query_text: str,
        *,
        top_k: int = 5,
        access_context: RagSearchAccessContext | None = None,
    ) -> list[RagSearchHit]:
        return self.repository.search_direct_match(
            collection_name,
            query_text,
            top_k=top_k,
            access_context=access_context,
        )


_KEYWORD_RETRIEVER = KeywordRetriever()


def get_keyword_retriever() -> KeywordRetriever:
    return _KEYWORD_RETRIEVER
