from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.memory.semantic_memory import SemanticMemoryHit
from app.chatbot.memory.short_term_memory import ShortTermMemoryContext
from app.chatbot.repositories.conversation_repository import ConversationRepository
from app.chatbot.repositories.memory_repository import MemoryRepository
from app.chatbot.repositories.message_repository import MessageRepository
from app.chatbot.services.context_service import ContextBundle, ContextService
from app.core.config import Settings
from app.db.base import Base
from app.db.models import User


@dataclass
class FakeSemanticRetriever:
    hits: list[SemanticMemoryHit] = field(default_factory=list)
    raise_error: bool = False
    calls: list[tuple[str, str, int | None]] = field(default_factory=list)

    def search(self, user_id: str, query_text: str, *, top_k: int | None = None, memory_type=None, conversation_id=None):
        self.calls.append((user_id, query_text, top_k))
        if self.raise_error:
            raise RuntimeError("semantic unavailable")
        return list(self.hits)


def _build_session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_engine(f"sqlite+pysqlite:///{(tmp_path / f'{uuid4()}.sqlite3').as_posix()}", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def _create_user(session: Session, *, email: str) -> User:
    user = User(email=email, display_name=email.split("@")[0].title(), hashed_password="hashed-password")
    session.add(user)
    session.flush()
    return user


def _settings(*, budget: int = 200, semantic_enabled: bool = True) -> Settings:
    return Settings(
        chatbot_env="development",
        chatbot_default_model="deepseek-chat",
        chatbot_message_max_chars=4000,
        chatbot_recent_message_limit=3,
        chatbot_context_token_budget=budget,
        chatbot_semantic_top_k=5,
        chatbot_semantic_candidate_multiplier=3,
        chatbot_semantic_similarity_threshold=0.72,
        chatbot_semantic_memory_enabled=semantic_enabled,
        chatbot_long_term_memory_enabled=True,
    )


def _seed_completed_turn(session_factory: sessionmaker[Session], owner_id: str, conversation_id: str, *, user_content: str, assistant_content: str) -> None:
    message_repo = MessageRepository(session_factory)
    user_message, assistant_message = message_repo.create_user_and_assistant(
        conversation_id,
        owner_id,
        content=user_content,
        client_request_id=str(uuid4()),
        assistant_model="deepseek-chat",
    )
    message_repo.finalize(
        assistant_message.id,
        owner_id,
        expected_status="pending",
        status="completed",
        content=assistant_content,
        model="deepseek-chat",
        prompt_tokens=1,
        completion_tokens=1,
        total_tokens=2,
    )


def _seed_summary(session_factory: sessionmaker[Session], conversation_id: str) -> None:
    with session_factory() as session:
        from app.chatbot.models.conversation import ChatbotConversationSummary

        now = datetime.now(timezone.utc)
        session.add(
            ChatbotConversationSummary(
                conversation_id=conversation_id,
                summary="summary context",
                start_sequence=1,
                end_sequence=4,
                summary_version=1,
                prompt_version="v1",
                model="deepseek-chat",
                token_count=10,
                status="completed",
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()


def test_context_service_builds_prioritized_bundle_and_dedupes_semantic_hits(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    conversation_repo = ConversationRepository(session_factory)
    memory_repo = MemoryRepository(session_factory)
    settings = _settings()
    fake_semantic = FakeSemanticRetriever()
    service = ContextService(
        session_factory=session_factory,
        settings=settings,
        memory_repository=memory_repo,
        semantic_retriever=fake_semantic,
    )

    with session_factory() as session:
        owner = _create_user(session, email="owner@example.com")
        session.commit()

    conversation = conversation_repo.create(owner.id, "Thread", "deepseek-chat", system_prompt_version="v1")
    _seed_summary(session_factory, conversation.id)
    _seed_completed_turn(session_factory, owner.id, conversation.id, user_content="recent user one", assistant_content="recent assistant one")
    _seed_completed_turn(session_factory, owner.id, conversation.id, user_content="recent user two", assistant_content="recent assistant two")

    active_record = memory_repo.create(
        owner.id,
        memory_type="project_context",
        content="memory alpha",
        normalized_hash="hash-alpha",
        conversation_id=conversation.id,
        importance=0.8,
        confidence=0.9,
        source_message_ids=[str(uuid4())],
        status="active",
        embedding_status="indexed",
    )
    memory_repo.create(
        owner.id,
        memory_type="project_context",
        content="memory beta",
        normalized_hash="hash-beta",
        conversation_id=conversation.id,
        importance=0.8,
        confidence=0.6,
        source_message_ids=[str(uuid4())],
        status="active",
        embedding_status="indexed",
    )
    memory_repo.create(
        owner.id,
        memory_type="project_context",
        content="memory expired",
        normalized_hash="hash-expired",
        conversation_id=conversation.id,
        importance=0.8,
        confidence=0.9,
        source_message_ids=[str(uuid4())],
        status="active",
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        embedding_status="indexed",
    )

    duplicate_hit = SemanticMemoryHit(
        memory_id=active_record.id,
        score=0.99,
        content="memory alpha",
        metadata={"memory_id": active_record.id, "user_id": owner.id, "memory_type": "project_context", "status": "active"},
        record=active_record,
    )
    unique_record = memory_repo.create(
        owner.id,
        memory_type="goal",
        content="memory gamma",
        normalized_hash="hash-gamma",
        conversation_id=conversation.id,
        importance=0.8,
        confidence=0.9,
        source_message_ids=[str(uuid4())],
        status="active",
        embedding_status="indexed",
    )
    unique_hit = SemanticMemoryHit(
        memory_id=unique_record.id,
        score=0.88,
        content="memory gamma",
        metadata={"memory_id": unique_record.id, "user_id": owner.id, "memory_type": "goal", "status": "active"},
        record=unique_record,
    )
    fake_semantic.hits = [duplicate_hit, unique_hit]

    bundle = service.build(owner.id, conversation.id, "current message")

    assert isinstance(bundle, ContextBundle)
    assert bundle.current_message == "current message"
    assert [section.kind for section in bundle.sections] == [
        "current_user",
        "recent",
        "recent",
        "recent",
        "summary",
        "long_term",
        "long_term",
    ]
    assert bundle.sections[0].trust_level == "trusted"
    assert all(section.kind != "semantic" for section in bundle.sections)
    assert {section.source_ids[0] for section in bundle.sections if section.kind == "long_term"} == {
        active_record.id,
        unique_record.id,
    }
    assert all(section.content for section in bundle.sections)
    assert bundle.token_estimate <= settings.chatbot_context_token_budget
    assert fake_semantic.calls == [(owner.id, "current message", settings.chatbot_semantic_top_k)]


def test_context_service_drops_low_priority_sections_before_recent_when_budget_is_tight(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    conversation_repo = ConversationRepository(session_factory)
    memory_repo = MemoryRepository(session_factory)
    settings = _settings(budget=40)
    fake_semantic = FakeSemanticRetriever()
    service = ContextService(
        session_factory=session_factory,
        settings=settings,
        memory_repository=memory_repo,
        semantic_retriever=fake_semantic,
    )

    with session_factory() as session:
        owner = _create_user(session, email="owner@example.com")
        session.commit()

    conversation = conversation_repo.create(owner.id, "Thread", "deepseek-chat", system_prompt_version="v1")
    _seed_summary(session_factory, conversation.id)
    _seed_completed_turn(session_factory, owner.id, conversation.id, user_content="older user", assistant_content="older assistant")
    memory_repo.create(
        owner.id,
        memory_type="project_context",
        content="long term memory that should be clipped first",
        normalized_hash="hash-alpha",
        conversation_id=conversation.id,
        importance=0.8,
        confidence=0.9,
        source_message_ids=[str(uuid4())],
        status="active",
        embedding_status="indexed",
    )

    bundle = service.build(owner.id, conversation.id, "current message that needs budget")

    kinds = [section.kind for section in bundle.sections]
    assert kinds[:3] == ["current_user", "recent", "recent"]
    assert "long_term" not in kinds
    assert "semantic" not in kinds
    assert bundle.token_estimate <= settings.chatbot_context_token_budget


def test_context_service_ignores_semantic_failures_and_keeps_bundle_building(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    conversation_repo = ConversationRepository(session_factory)
    memory_repo = MemoryRepository(session_factory)
    settings = _settings()
    fake_semantic = FakeSemanticRetriever(raise_error=True)
    service = ContextService(
        session_factory=session_factory,
        settings=settings,
        memory_repository=memory_repo,
        semantic_retriever=fake_semantic,
    )

    with session_factory() as session:
        owner = _create_user(session, email="owner@example.com")
        session.commit()

    conversation = conversation_repo.create(owner.id, "Thread", "deepseek-chat", system_prompt_version="v1")
    _seed_summary(session_factory, conversation.id)
    _seed_completed_turn(session_factory, owner.id, conversation.id, user_content="recent user", assistant_content="recent assistant")

    bundle = service.build(owner.id, conversation.id, "current message")

    assert bundle.current_message == "current message"
    assert all(section.kind != "semantic" for section in bundle.sections)
