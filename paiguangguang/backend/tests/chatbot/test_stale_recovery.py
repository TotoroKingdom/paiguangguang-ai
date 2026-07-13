from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, update
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.models.llm_run import ChatbotLLMRun
from app.chatbot.models.message import ChatbotMessage
from app.chatbot.repositories.conversation_repository import ConversationRepository
from app.chatbot.repositories.llm_run_repository import LLMRunRepository
from app.chatbot.repositories.message_repository import MessageRepository
from app.chatbot.services.recovery_service import RecoveryService
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


def test_recovery_service_marks_only_stale_runs_failed(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    conversation_repo = ConversationRepository(session_factory)
    message_repo = MessageRepository(session_factory)
    llm_run_repo = LLMRunRepository(session_factory)
    service = RecoveryService(
        session_factory,
        settings=Settings(chatbot_stale_run_seconds=60),
    )

    with session_factory() as session:
        owner = _create_user(session, email="owner@example.com")
        session.commit()

    conversation = conversation_repo.create(owner.id, "Thread", "deepseek-chat", system_prompt_version="v1")

    stale_user_message, stale_assistant_message = message_repo.create_user_and_assistant(
        conversation.id,
        owner.id,
        content="stale user message",
        client_request_id="00000000-0000-0000-0000-000000001001",
        assistant_model="deepseek-chat",
    )
    stale_run = llm_run_repo.create(
        request_id="00000000-0000-0000-0000-000000001002",
        user_id=owner.id,
        conversation_id=conversation.id,
        message_id=stale_assistant_message.id,
        provider="deepseek",
        model="deepseek-chat",
        prompt_version="v1",
    )

    fresh_user_message, fresh_assistant_message = message_repo.create_user_and_assistant(
        conversation.id,
        owner.id,
        content="fresh user message",
        client_request_id="00000000-0000-0000-0000-000000001003",
        assistant_model="deepseek-chat",
    )
    fresh_run = llm_run_repo.create(
        request_id="00000000-0000-0000-0000-000000001004",
        user_id=owner.id,
        conversation_id=conversation.id,
        message_id=fresh_assistant_message.id,
        provider="deepseek",
        model="deepseek-chat",
        prompt_version="v1",
    )

    stale_before = datetime.now(timezone.utc) - timedelta(minutes=10)
    with session_factory() as session:
        session.execute(update(ChatbotLLMRun).where(ChatbotLLMRun.id == stale_run.id).values(updated_at=stale_before))
        session.execute(update(ChatbotMessage).where(ChatbotMessage.id == stale_assistant_message.id).values(updated_at=stale_before))
        session.commit()

    recovered = service.reap_stale_runs(limit=10)
    assert recovered == 1

    with session_factory() as session:
        stale_run_model = session.get(ChatbotLLMRun, stale_run.id)
        fresh_run_model = session.get(ChatbotLLMRun, fresh_run.id)
        stale_message_model = session.get(ChatbotMessage, stale_assistant_message.id)
        fresh_message_model = session.get(ChatbotMessage, fresh_assistant_message.id)

    assert stale_run_model is not None
    assert stale_run_model.status == "failed"
    assert stale_run_model.error_code == "CHATBOT_STALE_GENERATION"
    assert stale_message_model is not None
    assert stale_message_model.status == "failed"
    assert stale_message_model.error_code == "CHATBOT_STALE_GENERATION"
    assert fresh_run_model is not None
    assert fresh_run_model.status == "pending"
    assert fresh_message_model is not None
    assert fresh_message_model.status == "pending"
