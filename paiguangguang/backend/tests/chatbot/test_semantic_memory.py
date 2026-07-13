from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.memory.memory_retriever import SemanticMemoryRetriever
from app.chatbot.memory.semantic_memory import SemanticMemoryIndex, build_semantic_memory_collection_name
from app.chatbot.repositories.conversation_repository import ConversationRepository
from app.chatbot.repositories.memory_repository import MemoryRepository
from app.core.config import Settings
from app.db.base import Base
from app.db.models import User


def _build_session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_engine(f"sqlite+pysqlite:///{(tmp_path / f'{uuid4()}.sqlite3').as_posix()}", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def _create_user(session: Session, *, email: str) -> User:
    user = User(email=email, display_name=email.split("@")[0].title(), hashed_password="hashed-password")
    session.add(user)
    session.flush()
    return user


@dataclass
class FakeEmbeddingProvider:
    dimension: int = 4

    def embed(self, texts):
        vectors = []
        for text in texts:
            lowered = text.lower()
            vectors.append(
                [
                    float(lowered.count("deep")),
                    float(lowered.count("theme")),
                    float(lowered.count("project")),
                    float(lowered.count("alpha")),
                ]
            )
        return vectors


@dataclass
class FakeCollection:
    name: str
    metadata: dict[str, object]
    records: dict[str, dict[str, object]] = field(default_factory=dict)
    last_query: dict[str, object] | None = None
    delete_calls: list[dict[str, object]] = field(default_factory=list)
    clear_count: int = 0

    def upsert(self, *, ids, documents, embeddings, metadatas):
        for index, memory_id in enumerate(ids):
            self.records[str(memory_id)] = {
                "document": documents[index],
                "embedding": embeddings[index],
                "metadata": dict(metadatas[index]),
            }

    def delete(self, *, ids=None, where=None):
        self.delete_calls.append({"ids": list(ids) if ids is not None else None, "where": where})
        if ids is not None:
            for memory_id in ids:
                self.records.pop(str(memory_id), None)
            return
        if where == {}:
            self.records.clear()
            self.clear_count += 1
            return
        for memory_id, record in list(self.records.items()):
            metadata = record["metadata"]
            if _matches_where(metadata, where):
                self.records.pop(memory_id, None)

    def query(self, *, query_embeddings, n_results, include, where):
        self.last_query = {"query_embeddings": query_embeddings, "n_results": n_results, "include": include, "where": where}
        query = query_embeddings[0]
        rows = []
        for memory_id, record in self.records.items():
            metadata = record["metadata"]
            if not _matches_where(metadata, where):
                continue
            score = _cosine_similarity(query, record["embedding"])
            rows.append((score, memory_id, record))
        rows.sort(key=lambda item: (-item[0], item[1]))
        rows = rows[:n_results]
        return {
            "ids": [[memory_id for _, memory_id, _ in rows]],
            "documents": [[record["document"] for _, _, record in rows]],
            "metadatas": [[record["metadata"] for _, _, record in rows]],
            "distances": [[1.0 - score for score, _, _ in rows]],
        }


@dataclass
class FakeChromaClient:
    collections: dict[str, FakeCollection] = field(default_factory=dict)
    deleted_collections: list[str] = field(default_factory=list)

    def get_or_create_collection(self, name: str, metadata: dict[str, object] | None = None):
        collection = self.collections.get(name)
        if collection is None:
            collection = FakeCollection(name=name, metadata=dict(metadata or {}))
            self.collections[name] = collection
        return collection

    def delete_collection(self, name: str) -> None:
        self.deleted_collections.append(name)
        self.collections.pop(name, None)

    def list_collections(self):
        return [SimpleNamespace(name=name) for name in self.collections]


def _matches_where(metadata: dict[str, object], where: dict[str, object] | None) -> bool:
    if where is None:
        return True
    if "$and" in where:
        return all(_matches_where(metadata, clause) for clause in where["$and"])
    for key, value in where.items():
        if metadata.get(key) != value:
            return False
    return True


def _cosine_similarity(a, b) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _settings() -> Settings:
    return Settings(
        chatbot_env="development",
        chatbot_embedding_version="v1",
        chatbot_semantic_top_k=5,
        chatbot_semantic_candidate_multiplier=3,
        chatbot_semantic_similarity_threshold=0.72,
        chatbot_semantic_memory_enabled=True,
        chatbot_default_model="deepseek-chat",
        embedding_model="text-embedding-v1",
    )


def _seed_memory(
    repo: MemoryRepository,
    owner_id: str,
    *,
    conversation_id: str,
    memory_type: str,
    content: str,
    normalized_hash: str,
    status: str = "active",
    embedding_status: str = "pending",
) -> str:
    record = repo.create(
        owner_id,
        memory_type=memory_type,
        content=content,
        normalized_hash=normalized_hash,
        conversation_id=conversation_id,
        status=status,
        confidence=0.9,
        importance=0.8,
        source_message_ids=["00000000-0000-0000-0000-000000000111"],
        embedding_status=embedding_status,
    )
    return record.id


def test_semantic_memory_collection_name_metadata_and_revalidation(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    conversation_repo = ConversationRepository(session_factory)
    memory_repo = MemoryRepository(session_factory)
    client = FakeChromaClient()
    settings = _settings()
    index = SemanticMemoryIndex(client=client, embedding_provider=FakeEmbeddingProvider(), settings=settings)
    retriever = SemanticMemoryRetriever(index=index, memory_repository=memory_repo, settings=settings)

    assert index.collection_name == "chatbot_memory_development_v1"

    with session_factory() as session:
        owner = _create_user(session, email="owner@example.com")
        foreign = _create_user(session, email="foreign@example.com")
        session.commit()

    owner_conversation = conversation_repo.create(owner.id, "Thread", "deepseek-chat", system_prompt_version="v1")
    foreign_conversation = conversation_repo.create(foreign.id, "Foreign", "deepseek-chat", system_prompt_version="v1")

    valid_memory_id = _seed_memory(
        memory_repo,
        owner.id,
        conversation_id=owner_conversation.id,
        memory_type="project_context",
        content="deep theme project",
        normalized_hash="hash-valid",
    )
    valid_record = memory_repo.get_owned(valid_memory_id, owner.id)
    assert valid_record is not None
    index.upsert_memory(valid_record)

    ghost_record = memory_repo.create(
        owner.id,
        memory_type="project_context",
        content="deep theme ghost",
        normalized_hash="hash-ghost",
        conversation_id=owner_conversation.id,
        status="deleted",
        confidence=0.9,
        importance=0.8,
        source_message_ids=["00000000-0000-0000-0000-000000000222"],
        embedding_status="indexed",
    )
    ghost_collection = client.get_or_create_collection(index.collection_name, metadata={})
    ghost_collection.upsert(
        ids=["ghost-memory-id"],
        documents=["deep theme ghost"],
        embeddings=[[3.0, 1.0, 1.0, 0.0]],
        metadatas=[
            {
                "memory_id": "ghost-memory-id",
                "user_id": owner.id,
                "conversation_id": owner_conversation.id,
                "memory_type": "project_context",
                "status": "active",
                "embedding_model": settings.embedding_model,
                "embedding_version": settings.chatbot_embedding_version,
                "created_at_epoch": 1,
            }
        ],
    )
    foreign_collection = client.get_or_create_collection(index.collection_name, metadata={})
    foreign_collection.upsert(
        ids=["foreign-memory-id"],
        documents=["deep theme foreign"],
        embeddings=[[3.0, 1.0, 1.0, 0.0]],
        metadatas=[
            {
                "memory_id": "foreign-memory-id",
                "user_id": foreign.id,
                "conversation_id": foreign_conversation.id,
                "memory_type": "project_context",
                "status": "active",
                "embedding_model": settings.embedding_model,
                "embedding_version": settings.chatbot_embedding_version,
                "created_at_epoch": 1,
            }
        ],
    )

    hits = retriever.search(owner.id, "deep theme project", top_k=5)

    assert client.collections[index.collection_name].metadata["embedding_model"] == settings.embedding_model
    assert client.collections[index.collection_name].metadata["embedding_version"] == settings.chatbot_embedding_version
    assert client.collections[index.collection_name].last_query["where"] == {"$and": [{"user_id": owner.id}, {"status": "active"}]}
    assert client.collections[index.collection_name].last_query["n_results"] == 15
    assert [hit.memory_id for hit in hits] == [valid_memory_id]
    assert hits[0].score >= settings.chatbot_semantic_similarity_threshold


def test_semantic_memory_retriever_dedupes_threshold_and_delete(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    conversation_repo = ConversationRepository(session_factory)
    memory_repo = MemoryRepository(session_factory)
    client = FakeChromaClient()
    settings = _settings()
    index = SemanticMemoryIndex(client=client, embedding_provider=FakeEmbeddingProvider(), settings=settings)
    retriever = SemanticMemoryRetriever(index=index, memory_repository=memory_repo, settings=settings)

    with session_factory() as session:
        owner = _create_user(session, email="owner@example.com")
        session.commit()

    conversation = conversation_repo.create(owner.id, "Thread", "deepseek-chat", system_prompt_version="v1")
    active_one = _seed_memory(
        memory_repo,
        owner.id,
        conversation_id=conversation.id,
        memory_type="goal",
        content="deep theme project",
        normalized_hash="hash-active-one",
    )
    active_two = _seed_memory(
        memory_repo,
        owner.id,
        conversation_id=conversation.id,
        memory_type="goal",
        content="deep theme plan",
        normalized_hash="hash-active-two",
    )
    record_one = memory_repo.get_owned(active_one, owner.id)
    record_two = memory_repo.get_owned(active_two, owner.id)
    assert record_one is not None and record_two is not None
    index.upsert_memory(record_one)
    index.upsert_memory(record_two)

    collection = client.collections[index.collection_name]
    collection.upsert(
        ids=["duplicate-hit", "duplicate-hit"],
        documents=["deep theme project", "deep theme project"],
        embeddings=[[3.0, 1.0, 1.0, 0.0], [3.0, 1.0, 1.0, 0.0]],
        metadatas=[
            {
                "memory_id": active_one,
                "user_id": owner.id,
                "conversation_id": conversation.id,
                "memory_type": "goal",
                "status": "active",
                "embedding_model": settings.embedding_model,
                "embedding_version": settings.chatbot_embedding_version,
                "created_at_epoch": 1,
            },
            {
                "memory_id": active_one,
                "user_id": owner.id,
                "conversation_id": conversation.id,
                "memory_type": "goal",
                "status": "active",
                "embedding_model": settings.embedding_model,
                "embedding_version": settings.chatbot_embedding_version,
                "created_at_epoch": 1,
            },
        ],
    )
    collection.records["low-score"] = {
        "document": "unrelated text",
        "embedding": [0.0, 0.0, 0.0, 1.0],
        "metadata": {
            "memory_id": "low-score",
            "user_id": owner.id,
            "conversation_id": conversation.id,
            "memory_type": "goal",
            "status": "active",
            "embedding_model": settings.embedding_model,
            "embedding_version": settings.chatbot_embedding_version,
            "created_at_epoch": 1,
        },
    }

    hits = retriever.search(owner.id, "deep theme project", top_k=5)
    assert [hit.memory_id for hit in hits] == [active_one, active_two]

    index.delete_memory(active_one)
    collection_after_delete = client.collections[index.collection_name]
    assert active_one not in collection_after_delete.records
    assert active_two in collection_after_delete.records
