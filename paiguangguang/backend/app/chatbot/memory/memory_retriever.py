from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from app.chatbot.memory.semantic_memory import SemanticMemoryHit, SemanticMemoryIndex
from app.chatbot.repositories.memory_repository import MemoryRecord, MemoryRepository
from app.core.config import Settings, get_settings


@dataclass(frozen=True, slots=True)
class SemanticMemorySearchResult:
    hits: list[SemanticMemoryHit]
    collection_name: str


class SemanticMemoryRetriever:
    def __init__(
        self,
        *,
        index: SemanticMemoryIndex | None = None,
        memory_repository: MemoryRepository,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.index = index or SemanticMemoryIndex(settings=self.settings)
        self.memory_repository = memory_repository

    def search(
        self,
        user_id: str,
        query_text: str,
        *,
        top_k: int | None = None,
        memory_type: str | None = None,
        conversation_id: str | None = None,
    ) -> list[SemanticMemoryHit]:
        if not self.index.enabled:
            return []
        effective_top_k = top_k or self.settings.chatbot_semantic_top_k
        if effective_top_k < 1:
            return []

        candidate_count = max(
            effective_top_k,
            effective_top_k * max(1, self.settings.chatbot_semantic_candidate_multiplier),
        )
        where_clauses = [{"user_id": user_id}, {"status": "active"}]
        if memory_type is not None:
            where_clauses.append({"memory_type": memory_type})
        if conversation_id is not None:
            where_clauses.append({"conversation_id": conversation_id})
        where = {"$and": where_clauses}

        collection = self.index._collection()
        query_embedding = self.index.embedding_provider.embed([query_text])[0]
        result = collection.query(
            query_embeddings=[query_embedding],
            n_results=candidate_count,
            include=["documents", "metadatas", "distances"],
            where=where,
        )

        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        hits: list[SemanticMemoryHit] = []
        seen: set[str] = set()
        for index, memory_id in enumerate(ids):
            memory_id = str(memory_id)
            if memory_id in seen:
                continue
            seen.add(memory_id)
            score = max(0.0, 1.0 - float(distances[index] if index < len(distances) else 1.0))
            if score < self.settings.chatbot_semantic_similarity_threshold:
                continue
            record = self.memory_repository.get_owned(memory_id, user_id)
            if record is None or record.status != "active":
                continue
            if memory_type is not None and record.memory_type != memory_type:
                continue
            if conversation_id is not None and record.conversation_id != conversation_id:
                continue
            metadata = dict(metadatas[index] if index < len(metadatas) else {})
            hits.append(
                SemanticMemoryHit(
                    memory_id=memory_id,
                    score=score,
                    content=str(documents[index] if index < len(documents) else record.content),
                    metadata=metadata,
                    record=record,
                )
            )
            if len(hits) >= effective_top_k:
                break

        return hits

