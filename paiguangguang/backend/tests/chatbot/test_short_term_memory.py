from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.memory.redis_adapter import RedisShortTermMemoryAdapter, build_short_term_memory_key
from app.chatbot.memory.short_term_memory import ShortTermMemoryService
from app.chatbot.models.conversation import ChatbotConversation, ChatbotConversationSummary
from app.chatbot.models.message import ChatbotMessage
from app.chatbot.repositories.conversation_repository import ConversationRepository
from app.chatbot.repositories.message_repository import MessageRepository
from app.chatbot.llm.provider import LLMMessage
from app.core.config import Settings
from app.db.base import Base
from app.db.models import User


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


def _seed_history(
    session_factory: sessionmaker[Session],
    owner_id: str,
    conversation_id: str,
    *,
    label: str = "",
) -> None:
    conversation_repo = ConversationRepository(session_factory)
    message_repo = MessageRepository(session_factory)
    summary_at = datetime.now(timezone.utc)
    conversation_repo.lock_owned(conversation_id, owner_id)
    with session_factory() as session:
        summary = ChatbotConversationSummary(
            conversation_id=conversation_id,
            summary="latest summary",
            start_sequence=1,
            end_sequence=2,
            summary_version=2,
            prompt_version="v1",
            model="deepseek-chat",
            token_count=42,
            status="completed",
            created_at=summary_at,
            updated_at=summary_at,
        )
        session.add(summary)
        session.flush()
        session.commit()

    with session_factory() as session:
        for index in range(1, 6):
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
            session.add_all([user_message, assistant_message])
        session.commit()


def test_short_term_memory_builds_versioned_keys_and_ttls(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CHATBOT_ENV", "development")
    monkeypatch.setenv("CHATBOT_REDIS_SCHEMA_VERSION", "7")
    monkeypatch.setenv("CHATBOT_SHORT_MEMORY_TTL_SECONDS", "123")

    key = build_short_term_memory_key(
        environment="development",
        schema_version=7,
        user_id="user 1",
        conversation_id="conv/1",
        memory_type="recent",
    )

    assert key == "chatbot:development:v7:user:user_1:conversation:conv_1:recent"


def test_short_term_memory_rebuilds_from_postgres_on_cache_miss_and_version_mismatch(tmp_path) -> None:
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
    _seed_history(session_factory, owner.id, conversation.id)

    service = ShortTermMemoryService(
        session_factory=session_factory,
        settings=settings,
        redis_module=SimpleNamespace(from_url=lambda url, decode_responses: fake_redis),
    )

    with session_factory() as session:
        snapshot = service.load_context(session, owner.id, conversation.id)

    assert snapshot.summary == "latest summary"
    assert [message.content for message in snapshot.recent_messages] == [
        "assistant-4",
        "user-5",
        "assistant-5",
    ]
    assert snapshot.state["schema_version"] == 7
    assert len(fake_redis.ttl_calls) == 3
    assert all(ttl == 123 for _, ttl in fake_redis.ttl_calls)

    # Corrupt the cached version and force a rebuild from PostgreSQL.
    for key, payload in list(fake_redis.stored.items()):
        fake_redis.stored[key] = payload.replace('"schema_version":7', '"schema_version":6')

        with session_factory() as session:
            session.execute(
                ChatbotMessage.__table__.update()
                .where(ChatbotMessage.conversation_id == conversation.id, ChatbotMessage.sequence_number == 10)
                .values(content="assistant-5-updated")
            )
            session.commit()

    with session_factory() as session:
        rebuilt = service.load_context(session, owner.id, conversation.id)

    assert [message.content for message in rebuilt.recent_messages][-1] == "assistant-5-updated"
    assert rebuilt.summary == "latest summary"


def test_short_term_memory_ignores_redis_failures_and_keeps_users_isolated(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)

    class FailingRedis:
        def ping(self):
            raise RuntimeError("redis down")

        def get(self, key: str):
            raise RuntimeError("redis down")

        def setex(self, key: str, ttl: int, value: str):
            raise RuntimeError("redis down")

    settings = Settings(
        redis_url="redis://localhost:6379/0",
        chatbot_env="development",
        chatbot_redis_schema_version=7,
        chatbot_short_memory_ttl_seconds=123,
        chatbot_recent_message_limit=2,
    )

    with session_factory() as session:
        owner = _create_user(session, email="owner@example.com")
        foreign = _create_user(session, email="foreign@example.com")
        session.commit()

    conversation_repo = ConversationRepository(session_factory)
    owner_conversation = conversation_repo.create(owner.id, "Owner", "deepseek-chat", system_prompt_version="v1")
    foreign_conversation = conversation_repo.create(foreign.id, "Foreign", "deepseek-chat", system_prompt_version="v1")
    _seed_history(session_factory, owner.id, owner_conversation.id, label="owner-")
    _seed_history(session_factory, foreign.id, foreign_conversation.id, label="foreign-")

    service = ShortTermMemoryService(
        session_factory=session_factory,
        settings=settings,
        redis_module=SimpleNamespace(from_url=lambda url, decode_responses: FailingRedis()),
    )

    with session_factory() as session:
        owner_snapshot = service.load_context(session, owner.id, owner_conversation.id)
        foreign_snapshot = service.load_context(session, foreign.id, foreign_conversation.id)

    assert owner_snapshot.summary == "latest summary"
    assert foreign_snapshot.summary == "latest summary"
    assert owner_snapshot.recent_messages != foreign_snapshot.recent_messages
