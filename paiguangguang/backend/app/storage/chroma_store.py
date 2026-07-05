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
    page_number: int | None
    chunk_index: int
    text: str
    score: float
    start_char: int
    end_char: int
    metadata: dict[str, object]


@dataclass(frozen=True)
class RagSearchAccessContext:
    workspace_id: str | None = None
    user_id: str | None = None
    is_system_admin: bool = False
    allowed_permission_scopes: tuple[str, ...] = ("workspace",)
    allow_legacy_metadata: bool = False


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
            normalized_metadata = self._normalize_metadata(chunk_id, metadata)
            if not self._is_accessible(normalized_metadata, access_context):
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

    @staticmethod
    def _derive_doc_id(chunk_id: str) -> str:
        if "-chunk-" in chunk_id:
            return chunk_id.rsplit("-chunk-", 1)[0]
        return chunk_id

    def _normalize_metadata(self, chunk_id: str, metadata: dict[str, object] | None) -> dict[str, object]:
        metadata = dict(metadata or {})
        doc_id = metadata.get("doc_id") or metadata.get("document_id") or self._derive_doc_id(chunk_id)
        title = metadata.get("title") or None
        page_number = metadata.get("page_number")
        chunk_index = metadata.get("chunk_index")
        start_char = metadata.get("start_char")
        end_char = metadata.get("end_char")
        permission_scope = metadata.get("permission_scope") or None
        workspace_id = metadata.get("workspace_id") or None
        owner_user_id = metadata.get("owner_user_id") or None
        content_hash = metadata.get("content_hash") or None
        lifecycle_version = metadata.get("lifecycle_version")
        normalized = {
            "doc_id": str(doc_id),
            "title": title,
            "page_number": int(page_number) if page_number not in (None, "") else 1,
            "chunk_index": int(chunk_index) if chunk_index not in (None, "") else 0,
            "start_char": int(start_char) if start_char not in (None, "") else 0,
            "end_char": int(end_char) if end_char not in (None, "") else 0,
            "permission_scope": permission_scope,
            "workspace_id": workspace_id,
            "owner_user_id": owner_user_id,
            "content_hash": content_hash,
            "lifecycle_version": int(lifecycle_version) if lifecycle_version not in (None, "") else 1,
            "chunk_id": str(chunk_id),
        }
        normalized.update(metadata)
        return normalized

    def _is_accessible(
        self,
        metadata: dict[str, object],
        access_context: RagSearchAccessContext | None,
    ) -> bool:
        if access_context is None:
            return True

        workspace_id = metadata.get("workspace_id")
        permission_scope = metadata.get("permission_scope")
        if workspace_id in (None, "") or permission_scope in (None, ""):
            return access_context.allow_legacy_metadata

        if access_context.is_system_admin:
            return True

        if access_context.workspace_id is not None and str(workspace_id) != access_context.workspace_id:
            return False

        return str(permission_scope) in access_context.allowed_permission_scopes


_CHROMA_RAG_STORE = ChromaRagStore()


def get_chroma_rag_store() -> ChromaRagStore:
    return _CHROMA_RAG_STORE
