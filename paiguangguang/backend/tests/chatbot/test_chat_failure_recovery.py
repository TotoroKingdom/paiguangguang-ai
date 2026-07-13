from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.llm.exceptions import LLMTimeoutError
from app.chatbot.llm.provider import ChatCompletionRequest
from app.chatbot.repositories.conversation_repository import ConversationRepository
from app.chatbot.repositories.llm_run_repository import LLMRunRepository
from app.chatbot.repositories.message_repository import MessageRepository
from app.chatbot.services.chat_service import ChatService
from app.core.config import Settings
from app.db.base import Base
from app.db.models import User


@dataclass
class FakeLLMClient:
    outcomes: list[object] = field(default_factory=list)
    complete_calls: list[ChatCompletionRequest] = field(default_factory=list)

    def complete(self, request: ChatCompletionRequest):
        self.complete_calls.append(request)
        if not self.outcomes:
            raise AssertionError("Unexpected LLM call")
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def close(self) -> None:
        return None


def _build_session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_engine(f"sqlite+pysqlite:///{(tmp_path / f'{uuid4()}.sqlite3').as_posix()}", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def _create_user(session: Session, *, email: str) -> User:
    user = User(email=email, display_name="Chatbot User", hashed_password="hashed-password")
    session.add(user)
    session.flush()
    return user


def _build_service(session_factory: sessionmaker[Session], llm_client: FakeLLMClient | None = None) -> ChatService:
    return ChatService(
        session_factory=session_factory,
        llm_client=llm_client,
        settings=Settings(
            chatbot_default_model="deepseek-chat",
            chatbot_allowed_models=["deepseek-chat"],
            chatbot_message_max_chars=4000,
            chatbot_recent_message_limit=20,
        ),
    )


def test_chat_service_marks_failed_turn_and_replays_it_without_second_llm_call(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    conversation_repo = ConversationRepository(session_factory)
    fake_llm = FakeLLMClient(outcomes=[LLMTimeoutError("request timed out")])
    service = _build_service(session_factory, fake_llm)

    with session_factory() as session:
        owner = _create_user(session, email="owner@example.com")
        session.commit()

    conversation = conversation_repo.create(owner.id, "Thread", "deepseek-chat", system_prompt_version="v1")
    client_request_id = "00000000-0000-0000-0000-000000000777"

    failed = service.complete(
        owner.id,
        conversation.id,
        "Please answer this request",
        client_request_id,
    )
    replay = service.complete(
        owner.id,
        conversation.id,
        "Please answer this request",
        client_request_id,
    )

    assert failed.replayed is False
    assert failed.assistant_message.status == "failed"
    assert failed.assistant_message.error_code == "CHATBOT_LLM_TIMEOUT"
    assert failed.llm_run.status == "failed"
    assert failed.llm_run.error_code == "CHATBOT_LLM_TIMEOUT"
    assert failed.llm_run.error_message == "LLM request timed out"
    assert replay.replayed is True
    assert replay.assistant_message.id == failed.assistant_message.id
    assert replay.llm_run.status == "failed"
    assert len(fake_llm.complete_calls) == 1


def test_chat_service_replays_pending_turn_without_second_llm_call(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    conversation_repo = ConversationRepository(session_factory)
    message_repo = MessageRepository(session_factory)
    llm_run_repo = LLMRunRepository(session_factory)
    fake_llm = FakeLLMClient()
    service = _build_service(session_factory, fake_llm)

    with session_factory() as session:
        owner = _create_user(session, email="owner@example.com")
        session.commit()

    conversation = conversation_repo.create(owner.id, "Thread", "deepseek-chat", system_prompt_version="v1")
    user_message, assistant_message = message_repo.create_user_and_assistant(
        conversation.id,
        owner.id,
        content="Please keep this request pending",
        client_request_id="00000000-0000-0000-0000-000000000889",
        assistant_model="deepseek-chat",
    )
    llm_run_repo.create(
        request_id="00000000-0000-0000-0000-000000000889",
        user_id=owner.id,
        conversation_id=conversation.id,
        message_id=assistant_message.id,
        provider="deepseek",
        model="deepseek-chat",
        prompt_version="v1",
    )

    replay = service.complete(
        owner.id,
        conversation.id,
        "Please keep this request pending",
        "00000000-0000-0000-0000-000000000889",
    )

    assert replay.replayed is True
    assert str(replay.user_message.id) == user_message.id
    assert replay.assistant_message.status == "pending"
    assert replay.llm_run.status == "pending"
    assert len(fake_llm.complete_calls) == 0
