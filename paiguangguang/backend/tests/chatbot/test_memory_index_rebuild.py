from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.commands.rebuild_memory_index import MemoryIndexRebuilder
from app.chatbot.memory.semantic_memory import SemanticMemoryIndex
from app.chatbot.repositories.conversation_repository import ConversationRepository
from app.chatbot.repositories.memory_repository import MemoryRepository
from app.core.config import Settings
from app.db.base import Base
from app.db.models import User

from tests.chatbot.test_semantic_memory import FakeChromaClient, FakeEmbeddingProvider, _seed_memory


def _build_session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_engine(f"sqlite+pysqlite:///{(tmp_path / f'{uuid4()}.sqlite3').as_posix()}", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def _create_user(session: Session, *, email: str) -> User:
    user = User(email=email, display_name=email.split("@")[0].title(), hashed_password="hashed-password")
    session.add(user)
    session.flush()
    return user


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


def test_memory_index_rebuild_dry_run_and_apply(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    conversation_repo = ConversationRepository(session_factory)
    memory_repo = MemoryRepository(session_factory)
    client = FakeChromaClient()
    settings = _settings()
    index = SemanticMemoryIndex(client=client, embedding_provider=FakeEmbeddingProvider(), settings=settings)
    rebuilder = MemoryIndexRebuilder(memory_repository=memory_repo, semantic_index=index, settings=settings)

    with session_factory() as session:
        owner = _create_user(session, email="owner@example.com")
        session.commit()

    conversation = conversation_repo.create(owner.id, "Thread", "deepseek-chat", system_prompt_version="v1")
    active_one = _seed_memory(
        memory_repo,
        owner.id,
        conversation_id=conversation.id,
        memory_type="project_context",
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
    _seed_memory(
        memory_repo,
        owner.id,
        conversation_id=conversation.id,
        memory_type="preference",
        content="candidate memory",
        normalized_hash="hash-candidate",
        status="candidate",
    )

    dry_run = rebuilder.dry_run(owner.id)
    assert dry_run.active_count == 2
    assert dry_run.collection_name == index.collection_name
    assert dry_run.checksum

    collection = client.get_or_create_collection(index.collection_name, metadata={})
    collection.upsert(
        ids=["stale-memory"],
        documents=["stale"],
        embeddings=[[0.0, 0.0, 0.0, 1.0]],
        metadatas=[
            {
                "memory_id": "stale-memory",
                "user_id": owner.id,
                "conversation_id": conversation.id,
                "memory_type": "goal",
                "status": "active",
                "embedding_model": settings.embedding_model,
                "embedding_version": settings.chatbot_embedding_version,
                "created_at_epoch": 1,
            }
        ],
    )

    report = rebuilder.apply(owner.id)

    assert report.active_count == 2
    assert report.collection_name == index.collection_name
    assert set(client.collections[index.collection_name].records) == {active_one, active_two}
    assert "stale-memory" not in client.collections[index.collection_name].records
    assert client.deleted_collections[-1] == index.collection_name
