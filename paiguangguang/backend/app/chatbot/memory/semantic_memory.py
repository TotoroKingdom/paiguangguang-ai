from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from threading import Lock
import re
from typing import Sequence

import chromadb

from app.ai.embeddings import CachingEmbeddingProvider, EmbeddingProvider, get_embedding_provider
from app.chatbot.repositories.memory_repository import MemoryRecord, MemoryRepository
from app.core.config import Settings, get_settings
from app.services.rag_cache import get_rag_cache_adapter


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    return normalized.strip("_") or "default"


def build_semantic_memory_collection_name(settings: Settings) -> str:
    return f"chatbot_memory_{_slugify(settings.chatbot_env)}_{_slugify(settings.chatbot_embedding_version)}"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class SemanticMemoryHit:
    memory_id: str
    score: float
    content: str
    metadata: dict[str, object]
    record: MemoryRecord


@dataclass(frozen=True, slots=True)
class SemanticMemoryRebuildReport:
    collection_name: str
    active_count: int
    checksum: str
    switched: bool = False


class SemanticMemoryIndex:
    def __init__(
        self,
        *,
        client: chromadb.api.ClientAPI | None = None,
        embedding_provider: EmbeddingProvider | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.client = client or chromadb.PersistentClient(path=self.settings.chroma_path)
        provider = embedding_provider or get_embedding_provider(self.settings)
        if isinstance(provider, CachingEmbeddingProvider):
            self.embedding_provider = provider
        else:
            self.embedding_provider = CachingEmbeddingProvider(
                provider=provider,
                cache_adapter=get_rag_cache_adapter(self.settings),
                model_version=getattr(provider, "model", provider.__class__.__name__),
            )
        self.collection_name = build_semantic_memory_collection_name(self.settings)
        self._lock = Lock()

    def _collection(self):
        with self._lock:
            return self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={
                    "hnsw:space": "cosine",
                    "embedding_model": self.settings.embedding_model,
                    "embedding_version": self.settings.chatbot_embedding_version,
                },
            )

    @property
    def enabled(self) -> bool:
        return bool(self.settings.chatbot_semantic_memory_enabled)

    def upsert_memory(self, record: MemoryRecord) -> None:
        if not self.enabled:
            return
        if record.status != "active":
            self.delete_memory(record.id)
            return

        collection = self._collection()
        embedding = self.embedding_provider.embed([record.content])[0]
        metadata = self._metadata_for_record(record)
        collection.upsert(
            ids=[record.id],
            documents=[record.content],
            embeddings=[embedding],
            metadatas=[metadata],
        )

    def delete_memory(self, memory_id: str) -> None:
        if not self.enabled:
            return
        collection = self._collection()
        collection.delete(ids=[memory_id])

    def delete_all(self) -> None:
        if not self.enabled:
            return
        with self._lock:
            delete_collection = getattr(self.client, "delete_collection", None)
            if callable(delete_collection):
                try:
                    delete_collection(self.collection_name)
                except Exception:
                    pass
            self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={
                    "hnsw:space": "cosine",
                    "embedding_model": self.settings.embedding_model,
                    "embedding_version": self.settings.chatbot_embedding_version,
                },
            )

    def rebuild(self, records: Sequence[MemoryRecord]) -> int:
        if not self.enabled:
            return 0
        self.delete_all()
        count = 0
        for record in records:
            if record.status != "active":
                continue
            self.upsert_memory(record)
            count += 1
        return count

    def checksum(self, records: Sequence[MemoryRecord]) -> str:
        digest = sha256()
        for record in sorted(records, key=lambda item: (item.user_id, item.memory_type, item.id)):
            digest.update(record.id.encode("utf-8"))
            digest.update(b"\0")
            digest.update(record.user_id.encode("utf-8"))
            digest.update(b"\0")
            digest.update(record.memory_type.encode("utf-8"))
            digest.update(b"\0")
            digest.update(record.normalized_hash.encode("utf-8"))
        return digest.hexdigest()

    def _metadata_for_record(self, record: MemoryRecord) -> dict[str, object]:
        return {
            "memory_id": record.id,
            "user_id": record.user_id,
            "conversation_id": record.conversation_id or "",
            "memory_type": record.memory_type,
            "status": record.status,
            "embedding_model": self.settings.embedding_model,
            "embedding_version": self.settings.chatbot_embedding_version,
            "created_at_epoch": int((record.created_at or _utcnow()).timestamp()),
        }


class MemoryIndexRebuilder:
    def __init__(
        self,
        *,
        memory_repository: MemoryRepository,
        semantic_index: SemanticMemoryIndex,
        settings: Settings | None = None,
    ) -> None:
        self.memory_repository = memory_repository
        self.semantic_index = semantic_index
        self.settings = settings or get_settings()

    def _iter_active_records(self, user_id: str) -> list[MemoryRecord]:
        records: list[MemoryRecord] = []
        cursor: str | None = None
        while True:
            page = self.memory_repository.list_owned_page(
                user_id,
                status="active",
                cursor=cursor,
                limit=100,
            )
            records.extend(page.items)
            if not page.has_more or not page.next_cursor:
                break
            cursor = page.next_cursor
        return records

    def count(self, user_id: str) -> int:
        return len(self._iter_active_records(user_id))

    def checksum(self, user_id: str) -> str:
        return self.semantic_index.checksum(self._iter_active_records(user_id))

    def dry_run(self, user_id: str) -> SemanticMemoryRebuildReport:
        records = self._iter_active_records(user_id)
        return SemanticMemoryRebuildReport(
            collection_name=self.semantic_index.collection_name,
            active_count=len(records),
            checksum=self.semantic_index.checksum(records),
            switched=False,
        )

    def apply(self, user_id: str) -> SemanticMemoryRebuildReport:
        records = self._iter_active_records(user_id)
        self.semantic_index.rebuild(records)
        return SemanticMemoryRebuildReport(
            collection_name=self.semantic_index.collection_name,
            active_count=len(records),
            checksum=self.semantic_index.checksum(records),
            switched=True,
        )

    def switch(self, user_id: str) -> SemanticMemoryRebuildReport:
        return self.apply(user_id)

