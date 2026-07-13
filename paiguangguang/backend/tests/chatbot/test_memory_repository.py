from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.models.memory import ChatbotMemory
from app.chatbot.repositories.conversation_repository import ConversationRepository
from app.chatbot.repositories.memory_repository import MemoryRepository
from app.db.models import Base, User


def _build_session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_engine(f"sqlite+pysqlite:///{(tmp_path / f'{uuid4()}.sqlite3').as_posix()}", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def _create_user(session: Session, *, email: str) -> User:
    user = User(email=email, display_name="Chatbot User", hashed_password="hashed-password")
    session.add(user)
    session.flush()
    return user


def _create_conversation(repo: ConversationRepository, user_id: str, title: str) -> str:
    conversation = repo.create(user_id, title, "deepseek-chat")
    return conversation.id


def test_create_dedupes_by_normalized_hash_and_keeps_owner_scope(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    conversation_repo = ConversationRepository(session_factory)
    repo = MemoryRepository(session_factory)

    with session_factory() as session:
        owner = _create_user(session, email="owner@example.com")
        foreign = _create_user(session, email="foreign@example.com")
        session.commit()

    conversation_id = _create_conversation(conversation_repo, owner.id, "Thread")

    first = repo.create(
        owner.id,
        memory_type="fact",
        content="同义归一",
        normalized_hash="hash-001",
        conversation_id=conversation_id,
        source_message_ids=["00000000-0000-0000-0000-000000000111"],
    )
    second = repo.create(
        owner.id,
        memory_type="fact",
        content="同义归一但不同文本",
        normalized_hash="hash-001",
        conversation_id=conversation_id,
    )

    assert second.id == first.id
    assert second.content == first.content
    assert repo.get_owned(first.id, foreign.id) is None
    assert repo.get_owned(first.id, owner.id) is not None


def test_list_owned_filters_active_candidate_and_expiry(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    conversation_repo = ConversationRepository(session_factory)
    repo = MemoryRepository(session_factory)

    with session_factory() as session:
        owner = _create_user(session, email="owner@example.com")
        session.commit()

    conversation_id = _create_conversation(conversation_repo, owner.id, "Thread")
    now = datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc)

    active_future = repo.create(
        owner.id,
        memory_type="project_context",
        content="active future",
        normalized_hash="hash-active-future",
        conversation_id=conversation_id,
        expires_at=now + timedelta(days=1),
    )
    expired_active = repo.create(
        owner.id,
        memory_type="project_context",
        content="expired active",
        normalized_hash="hash-active-expired",
        conversation_id=conversation_id,
        expires_at=now - timedelta(days=1),
    )
    candidate = repo.create(
        owner.id,
        memory_type="goal",
        content="candidate",
        normalized_hash="hash-candidate",
        conversation_id=conversation_id,
    )

    with session_factory() as session:
        active_row = session.get(ChatbotMemory, active_future.id)
        if active_row is not None:
            active_row.status = "active"
            active_row.updated_at = now
        expired_row = session.get(ChatbotMemory, expired_active.id)
        if expired_row is not None:
            expired_row.status = "active"
            expired_row.updated_at = now + timedelta(minutes=1)
        candidate_row = session.get(ChatbotMemory, candidate.id)
        if candidate_row is not None:
            candidate_row.status = "candidate"
            candidate_row.updated_at = now + timedelta(minutes=2)
        session.commit()

    active_items = repo.list_owned(owner.id, status="active")
    candidate_items = repo.list_owned(owner.id, status="candidate")
    all_items = repo.list_owned(owner.id, status=None)

    assert [item.id for item in active_items] == [active_future.id]
    assert [item.id for item in candidate_items] == [candidate.id]
    assert [item.id for item in all_items] == [candidate.id, active_future.id]
    assert expired_active.id not in {item.id for item in active_items}


def test_soft_delete_and_embedding_backlog_claim(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    conversation_repo = ConversationRepository(session_factory)
    repo = MemoryRepository(session_factory)

    with session_factory() as session:
        owner = _create_user(session, email="owner@example.com")
        session.commit()

    conversation_id = _create_conversation(conversation_repo, owner.id, "Thread")

    first = repo.create(
        owner.id,
        memory_type="fact",
        content="first",
        normalized_hash="hash-first",
        conversation_id=conversation_id,
    )
    second = repo.create(
        owner.id,
        memory_type="fact",
        content="second",
        normalized_hash="hash-second",
        conversation_id=conversation_id,
    )
    third = repo.create(
        owner.id,
        memory_type="fact",
        content="third",
        normalized_hash="hash-third",
        conversation_id=conversation_id,
    )

    with session_factory() as session:
        first_row = session.get(ChatbotMemory, first.id)
        second_row = session.get(ChatbotMemory, second.id)
        third_row = session.get(ChatbotMemory, third.id)
        if first_row is not None:
            first_row.updated_at = datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc)
        if second_row is not None:
            second_row.updated_at = datetime(2026, 7, 13, 12, 1, tzinfo=timezone.utc)
        if third_row is not None:
            third_row.updated_at = datetime(2026, 7, 13, 12, 2, tzinfo=timezone.utc)
        session.commit()

    claimed = repo.claim_embedding_backlog(owner.id, limit=2)
    assert [item.id for item in claimed] == [third.id, second.id]

    deleted = repo.soft_delete(first.id, owner.id)
    assert deleted is not None
    assert deleted.status == "deleted"
    assert deleted.embedding_status == "deleted"
    assert deleted.deleted_at is not None
    assert repo.get_owned(first.id, owner.id) is None
