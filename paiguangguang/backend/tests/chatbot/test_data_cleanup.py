from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.commands.rebuild_memory_index import MemoryIndexRebuilder
from app.chatbot.memory.semantic_memory import SemanticMemoryIndex
from app.chatbot.memory.short_term_memory import ShortTermMemoryService
from app.chatbot.models.conversation import ChatbotConversation
from app.chatbot.models.memory import ChatbotMemory
from app.chatbot.models.message import ChatbotMessage
from app.chatbot.repositories.conversation_repository import ConversationRepository
from app.chatbot.repositories.memory_repository import MemoryRepository
from app.chatbot.repositories.message_repository import MessageRepository
from app.chatbot.services.conversation_service import ConversationService
from app.chatbot.services.memory_service import MemoryService
from app.core.config import Settings
from app.db.base import Base
from app.db.models import User
from tests.chatbot.test_semantic_memory import FakeChromaClient, FakeEmbeddingProvider, _seed_memory


@dataclass
class FakeRedisClient:
    stored: dict[str, str] | None = None
    ttl_calls: list[tuple[str, int]] | None = None
    deleted: list[str] | None = None

    def __post_init__(self) -> None:
        self.stored = {} if self.stored is None else self.stored
        self.ttl_calls = [] if self.ttl_calls is None else self.ttl_calls
        self.deleted = [] if self.deleted is None else self.deleted

    def ping(self) -> None:
        return None

    def get(self, key: str) -> str | None:
        return self.stored.get(key)

    def setex(self, key: str, ttl: int, value: str) -> None:
        self.ttl_calls.append((key, ttl))
        self.stored[key] = value

    def set(self, key: str, value: str) -> None:
        self.stored[key] = value

    def delete(self, *keys: str) -> None:
        self.deleted.extend(keys)
        for key in keys:
            self.stored.pop(key, None)

    def keys(self, pattern: str) -> list[str]:
        prefix = pattern[:-1] if pattern.endswith("*") else pattern
        return [key for key in self.stored if key.startswith(prefix)]


def _build_session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_engine(f"sqlite+pysqlite:///{(tmp_path / f'{uuid4()}.sqlite3').as_posix()}", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def _create_user(session: Session, *, email: str) -> User:
    user = User(email=email, display_name=email.split("@")[0].title(), hashed_password="hashed-password")
    session.add(user)
    session.flush()
    return user


def _seed_turn(
    session_factory: sessionmaker[Session],
    owner_id: str,
    conversation_id: str,
    *,
    label: str = "",
) -> None:
    message_repo = MessageRepository(session_factory)
    summary_at = datetime.now(timezone.utc)
    with session_factory() as session:
        from app.chatbot.models.conversation import ChatbotConversationSummary

        session.add(
            ChatbotConversationSummary(
                conversation_id=conversation_id,
                summary="latest summary",
                start_sequence=1,
                end_sequence=2,
                summary_version=1,
                prompt_version="v1",
                model="deepseek-chat",
                token_count=12,
                status="completed",
                created_at=summary_at,
                updated_at=summary_at,
            )
        )
        session.commit()

    for index in range(1, 4):
        user_message = ChatbotMessage(
            id=str(uuid4()),
            conversation_id=conversation_id,
            user_id=owner_id,
            role="user",
            content=f"{label}user-{index}",
            content_json=None,
            sequence_number=index * 2 - 1,
            status="completed",
            model=None,
            parent_message_id=None,
            client_request_id=str(uuid4()),
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            error_code=None,
            created_at=summary_at,
            updated_at=summary_at,
        )
        assistant_message = ChatbotMessage(
            id=str(uuid4()),
            conversation_id=conversation_id,
            user_id=owner_id,
            role="assistant",
            content=f"{label}assistant-{index}",
            content_json=None,
            sequence_number=index * 2,
            status="completed",
            model="deepseek-chat",
            parent_message_id=user_message.id,
            client_request_id=None,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            error_code=None,
            created_at=summary_at,
            updated_at=summary_at,
        )
        with session_factory() as session:
            session.add_all([user_message, assistant_message])
            session.commit()


def test_data_cleanup_short_term_cache_misses_rebuild_and_deleted_conversation_rejects_load(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    fake_redis = FakeRedisClient()
    settings = Settings(
        redis_url="redis://localhost:6379/0",
        chatbot_env="development",
        chatbot_redis_schema_version=7,
        chatbot_short_memory_ttl_seconds=123,
        chatbot_recent_message_limit=3,
    )

    with session_factory() as session:
        owner = _create_user(session, email="owner@example.com")
        session.commit()

    conversation_repo = ConversationRepository(session_factory)
    conversation = conversation_repo.create(owner.id, "Thread", "deepseek-chat", system_prompt_version="v1")
    _seed_turn(session_factory, owner.id, conversation.id)

    service = ShortTermMemoryService(
        session_factory=session_factory,
        settings=settings,
        redis_module=SimpleNamespace(from_url=lambda url, decode_responses: fake_redis),
    )

    with session_factory() as session:
        snapshot = service.load_context(session, owner.id, conversation.id)

    assert snapshot.summary == "latest summary"
    assert [message.content for message in snapshot.recent_messages] == ["user-2", "assistant-2", "user-3", "assistant-3"][-3:]
    assert len(fake_redis.ttl_calls) == 3

    for key, payload in list(fake_redis.stored.items()):
        fake_redis.stored[key] = payload.replace('"schema_version":7', '"schema_version":6')

    with session_factory() as session:
        session.execute(
            ChatbotMessage.__table__.update()
            .where(ChatbotMessage.conversation_id == conversation.id, ChatbotMessage.sequence_number == 6)
            .values(content="assistant-3-updated")
        )
        session.commit()

    with session_factory() as session:
        rebuilt = service.load_context(session, owner.id, conversation.id)

    assert [message.content for message in rebuilt.recent_messages][-1] == "assistant-3-updated"

    with session_factory() as session:
        delete_result = ConversationService().delete_conversation(session, owner.id, conversation.id)
    assert delete_result.cleanup_status == "pending"

    with session_factory() as session:
        with pytest.raises(ValueError):
            service.load_context(session, owner.id, conversation.id)


def test_data_cleanup_deletes_semantic_index_entries_and_rebuilds_stale_chroma_records(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    memory_repo = MemoryRepository(session_factory)
    client = FakeChromaClient()
    settings = Settings(
        chatbot_env="development",
        chatbot_embedding_version="v1",
        chatbot_semantic_top_k=5,
        chatbot_semantic_candidate_multiplier=3,
        chatbot_semantic_similarity_threshold=0.72,
        chatbot_semantic_memory_enabled=True,
        chatbot_default_model="deepseek-chat",
        embedding_model="text-embedding-v1",
    )
    index = SemanticMemoryIndex(client=client, embedding_provider=FakeEmbeddingProvider(), settings=settings)
    rebuilder = MemoryIndexRebuilder(memory_repository=memory_repo, semantic_index=index, settings=settings)
    memory_service = MemoryService(session_factory=session_factory, settings=settings, semantic_index=index)

    with session_factory() as session:
        owner = _create_user(session, email="owner@example.com")
        session.commit()

    conversation_repo = ConversationRepository(session_factory)
    conversation = conversation_repo.create(owner.id, "Thread", "deepseek-chat", system_prompt_version="v1")
    active_memory = memory_repo.create(
        owner.id,
        memory_type="project_context",
        content="deep theme project",
        normalized_hash="hash-active",
        conversation_id=conversation.id,
        status="active",
        confidence=0.95,
        importance=0.8,
        source_message_ids=[str(uuid4())],
        embedding_status="indexed",
    )
    index.upsert_memory(memory_repo.get_owned(active_memory.id, owner.id))

    deleted = memory_service.delete_memory(session_factory(), owner.id, active_memory.id)
    assert deleted.status == "deleted"
    deleted_record = memory_repo.get_owned(active_memory.id, owner.id, include_deleted=True)
    assert deleted_record is not None
    assert deleted_record.embedding_status == "deleted"
    assert client.collections[index.collection_name].delete_calls[-1] == {"ids": [active_memory.id], "where": None}

    active_memory_id = _seed_memory(
        memory_repo,
        owner.id,
        conversation_id=conversation.id,
        memory_type="project_context",
        content="deep theme project",
        normalized_hash="hash-active",
    )
    with session_factory() as seed_session:
        stale_collection = client.get_or_create_collection(index.collection_name, metadata={})
        stale_collection.upsert(
            ids=["stale-memory"],
            documents=["stale"],
            embeddings=[[0.0, 0.0, 0.0, 1.0]],
            metadatas=[
                {
                    "memory_id": "stale-memory",
                    "user_id": owner.id,
                    "conversation_id": conversation.id,
                    "memory_type": "project_context",
                    "status": "active",
                    "embedding_model": settings.embedding_model,
                    "embedding_version": settings.chatbot_embedding_version,
                    "created_at_epoch": 1,
                }
            ],
        )

    report = rebuilder.apply(owner.id)
    assert report.active_count >= 1
    assert "stale-memory" not in client.collections[index.collection_name].records
    assert active_memory_id in client.collections[index.collection_name].records
