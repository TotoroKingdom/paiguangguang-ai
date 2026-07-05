from __future__ import annotations

from threading import Lock
from typing import Sequence

import chromadb

from app.ai.embeddings import CachingEmbeddingProvider, EmbeddingProvider, get_embedding_provider
from app.core.config import get_settings
from app.storage.rag_documents import RagChunkRecord
from app.storage.rag_search import (
    RagSearchAccessContext,
    RagSearchHit,
    is_rag_search_accessible,
    normalize_rag_search_metadata,
)
from app.services.rag_cache import get_rag_cache_adapter


class ChromaRagStore:
    def __init__(
        self,
        client: chromadb.api.ClientAPI | None = None,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        settings = get_settings()
        self.client = client or chromadb.PersistentClient(path=settings.chroma_path)
        provider = embedding_provider or get_embedding_provider(settings)
        if isinstance(provider, CachingEmbeddingProvider):
            self.embedding_provider = provider
        else:
            self.embedding_provider = CachingEmbeddingProvider(
                provider=provider,
                cache_adapter=get_rag_cache_adapter(settings),
                model_version=getattr(provider, "model", provider.__class__.__name__),
            )
        self._lock = Lock()

    def _collection(self, collection_name: str):
        with self._lock:
            return self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )

    def index_ingestion(
        self,
        collection_name: str,
        *,
        doc_id: str,
        title: str | None,
        content_hash: str,
        chunks: Sequence[RagChunkRecord],
        owner_user_id: str | None = None,
        workspace_id: str | None = None,
        permission_scope: str | None = None,
        lifecycle_version: int = 1,
    ) -> int:
        if not chunks:
            return 0

        collection = self._collection(collection_name)
        embeddings = self.embedding_provider.embed([chunk.text for chunk in chunks])
        collection.upsert(
            ids=[chunk.chunk_id for chunk in chunks],
            documents=[chunk.text for chunk in chunks],
            embeddings=embeddings,
            metadatas=[
                {
                    "doc_id": doc_id,
                    "title": title or "",
                    "content_hash": content_hash,
                    "owner_user_id": owner_user_id or "",
                    "workspace_id": workspace_id or "",
                    "permission_scope": permission_scope or "",
                    "page_number": chunk.page_number or 0,
                    "chunk_id": chunk.chunk_id,
                    "chunk_index": chunk.index,
                    "start_char": chunk.start_char,
                    "end_char": chunk.end_char,
                    "lifecycle_version": lifecycle_version,
                }
                for chunk in chunks
            ],
        )
        return len(chunks)

    def search(
        self,
        collection_name: str,
        query_text: str,
        *,
        top_k: int = 5,
        access_context: RagSearchAccessContext | None = None,
    ) -> list[RagSearchHit]:
        collection = self._collection(collection_name)
        query_embeddings = self.embedding_provider.embed([query_text])
        result = collection.query(
            query_embeddings=query_embeddings,
            n_results=max(top_k * 5, top_k),
            include=["documents", "metadatas", "distances"],
        )

        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        hits: list[RagSearchHit] = []
        for index, chunk_id in enumerate(ids):
            metadata = metadatas[index] if index < len(metadatas) else {}
            document = documents[index] if index < len(documents) else ""
            distance = float(distances[index]) if index < len(distances) else 1.0
            normalized_metadata = normalize_rag_search_metadata(chunk_id, metadata)
            if not is_rag_search_accessible(normalized_metadata, access_context):
                continue
            hits.append(
                RagSearchHit(
                    doc_id=str(normalized_metadata["doc_id"]),
                    chunk_id=str(chunk_id),
                    title=normalized_metadata["title"],
                    page_number=normalized_metadata["page_number"],
                    chunk_index=normalized_metadata["chunk_index"],
                    text=str(document),
                    score=max(0.0, 1.0 - distance),
                    start_char=int(normalized_metadata["start_char"]),
                    end_char=int(normalized_metadata["end_char"]),
                    metadata=normalized_metadata,
                )
            )
            if len(hits) >= top_k:
                break

        return hits


_CHROMA_RAG_STORE = ChromaRagStore()


def get_chroma_rag_store() -> ChromaRagStore:
    return _CHROMA_RAG_STORE
