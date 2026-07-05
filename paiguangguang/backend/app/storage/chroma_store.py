from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Sequence

import chromadb

from app.ai.embeddings import EmbeddingProvider, get_embedding_provider
from app.core.config import get_settings
from app.storage.rag_documents import RagChunkRecord


@dataclass(frozen=True)
class RagSearchHit:
    doc_id: str
    chunk_id: str
    title: str | None
    text: str
    score: float
    index: int
    start_char: int
    end_char: int


class ChromaRagStore:
    def __init__(
        self,
        client: chromadb.api.ClientAPI | None = None,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        settings = get_settings()
        self.client = client or chromadb.PersistentClient(path=settings.chroma_path)
        self.embedding_provider = embedding_provider or get_embedding_provider(settings)
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
                    "chunk_id": chunk.chunk_id,
                    "chunk_index": chunk.index,
                    "start_char": chunk.start_char,
                    "end_char": chunk.end_char,
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
    ) -> list[RagSearchHit]:
        collection = self._collection(collection_name)
        query_embeddings = self.embedding_provider.embed([query_text])
        result = collection.query(
            query_embeddings=query_embeddings,
            n_results=top_k,
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
            hits.append(
                RagSearchHit(
                    doc_id=str(metadata.get("doc_id", "")),
                    chunk_id=str(chunk_id),
                    title=metadata.get("title") or None,
                    text=str(document),
                    score=max(0.0, 1.0 - distance),
                    index=int(metadata.get("chunk_index", 0)),
                    start_char=int(metadata.get("start_char", 0)),
                    end_char=int(metadata.get("end_char", 0)),
                )
            )

        return hits


_CHROMA_RAG_STORE = ChromaRagStore()


def get_chroma_rag_store() -> ChromaRagStore:
    return _CHROMA_RAG_STORE
