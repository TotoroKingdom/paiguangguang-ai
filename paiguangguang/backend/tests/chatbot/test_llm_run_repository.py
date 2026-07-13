from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.models.conversation import ChatbotConversation
from app.chatbot.models.llm_run import ChatbotLLMRun
from app.chatbot.repositories.conversation_repository import ConversationRepository
from app.chatbot.repositories.llm_run_repository import LLMRunRepository
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


def test_create_stream_finalize_and_get_active_run(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    conversation_repo = ConversationRepository(session_factory)
    repo = LLMRunRepository(session_factory)

    with session_factory() as session:
        user = _create_user(session, email="owner@example.com")
        session.commit()

    conversation_id = _create_conversation(conversation_repo, user.id, "Thread")

    run = repo.create(
        request_id="00000000-0000-0000-0000-000000001001",
        user_id=user.id,
        conversation_id=conversation_id,
        message_id="00000000-0000-0000-0000-000000001002",
        provider="deepseek",
        model="deepseek-chat",
        prompt_version="v1",
    )
    assert run.status == "pending"

    active = repo.get_active_for_conversation(conversation_id, user.id)
    assert active is not None
    assert active.id == run.id

    streaming = repo.mark_streaming(
        run.id,
        user.id,
        expected_status="pending",
        first_token_latency_ms=120,
    )
    assert streaming is not None
    assert streaming.status == "streaming"
    assert streaming.first_token_latency_ms == 120

    assert (
        repo.mark_streaming(
            run.id,
            user.id,
            expected_status="pending",
            first_token_latency_ms=240,
        )
        is None
    )

    completed = repo.finalize(
        run.id,
        user.id,
        expected_status="streaming",
        status="completed",
        prompt_tokens=10,
        completion_tokens=20,
        total_tokens=30,
        finish_reason="stop",
    )
    assert completed is not None
    assert completed.status == "completed"
    assert completed.finish_reason == "stop"
    assert completed.total_tokens == 30
    assert repo.get_active_for_conversation(conversation_id, user.id) is None


def test_scan_stale_runs_returns_pending_and_streaming_only(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    conversation_repo = ConversationRepository(session_factory)
    repo = LLMRunRepository(session_factory)

    with session_factory() as session:
        user = _create_user(session, email="owner@example.com")
        session.commit()

    conversation_id = _create_conversation(conversation_repo, user.id, "Thread")
    now = datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc)

    pending = repo.create(
        request_id="00000000-0000-0000-0000-000000002001",
        user_id=user.id,
        conversation_id=conversation_id,
        message_id="00000000-0000-0000-0000-000000002002",
        provider="deepseek",
        model="deepseek-chat",
        prompt_version="v1",
    )
    streaming = repo.create(
        request_id="00000000-0000-0000-0000-000000002003",
        user_id=user.id,
        conversation_id=conversation_id,
        message_id="00000000-0000-0000-0000-000000002004",
        provider="deepseek",
        model="deepseek-chat",
        prompt_version="v1",
    )
    completed = repo.create(
        request_id="00000000-0000-0000-0000-000000002005",
        user_id=user.id,
        conversation_id=conversation_id,
        message_id="00000000-0000-0000-0000-000000002006",
        provider="deepseek",
        model="deepseek-chat",
        prompt_version="v1",
    )

    with session_factory() as session:
        pending_row = session.get(ChatbotLLMRun, pending.id)
        streaming_row = session.get(ChatbotLLMRun, streaming.id)
        completed_row = session.get(ChatbotLLMRun, completed.id)
        assert pending_row is not None and streaming_row is not None and completed_row is not None
        pending_row.updated_at = now - timedelta(hours=2)
        streaming_row.updated_at = now - timedelta(hours=2, minutes=5)
        completed_row.updated_at = now - timedelta(hours=2, minutes=10)
        completed_row.status = "completed"
        session.commit()

    with session_factory() as session:
        streaming_row = session.get(ChatbotLLMRun, streaming.id)
        assert streaming_row is not None
        streaming_row.status = "streaming"
        session.commit()

    stale_runs = repo.scan_stale_runs(now - timedelta(hours=1), limit=10)
    assert [run.id for run in stale_runs] == [streaming.id, pending.id]


def test_owner_safe_lookup_blocks_foreign_user(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    conversation_repo = ConversationRepository(session_factory)
    repo = LLMRunRepository(session_factory)

    with session_factory() as session:
        owner = _create_user(session, email="owner@example.com")
        foreign = _create_user(session, email="foreign@example.com")
        session.commit()

    owner_conversation_id = _create_conversation(conversation_repo, owner.id, "Owner thread")
    foreign_conversation_id = _create_conversation(conversation_repo, foreign.id, "Foreign thread")

    owner_run = repo.create(
        request_id="00000000-0000-0000-0000-000000003001",
        user_id=owner.id,
        conversation_id=owner_conversation_id,
        message_id="00000000-0000-0000-0000-000000003002",
        provider="deepseek",
        model="deepseek-chat",
        prompt_version="v1",
    )
    foreign_run = repo.create(
        request_id="00000000-0000-0000-0000-000000003003",
        user_id=foreign.id,
        conversation_id=foreign_conversation_id,
        message_id="00000000-0000-0000-0000-000000003004",
        provider="deepseek",
        model="deepseek-chat",
        prompt_version="v1",
    )

    assert repo.get_owned(owner_run.id, foreign.id) is None
    assert repo.get_active_for_conversation(owner_conversation_id, foreign.id) is None
    assert repo.get_owned(foreign_run.id, foreign.id) is not None
