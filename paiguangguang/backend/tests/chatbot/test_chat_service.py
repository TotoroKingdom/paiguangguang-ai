from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.errors import ChatbotApiError
from app.chatbot.llm.provider import ChatCompletionRequest, ChatCompletionResult, ChatCompletionUsage, LLMMessage
from app.chatbot.models.conversation import ChatbotConversation
from app.chatbot.models.llm_run import ChatbotLLMRun
from app.chatbot.repositories.conversation_repository import ConversationRepository
from app.chatbot.repositories.llm_run_repository import LLMRunRepository
from app.chatbot.repositories.message_repository import MessageRepository
from app.chatbot.services.chat_service import ChatService
from app.core.config import Settings
from app.db.base import Base
from app.db.models import User


@dataclass
class FakeLLMClient:
    outcomes: list[ChatCompletionResult | Exception] = field(default_factory=list)
    complete_calls: list[ChatCompletionRequest] = field(default_factory=list)

    def complete(self, request: ChatCompletionRequest) -> ChatCompletionResult:
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


def _seed_completed_turn(session_factory: sessionmaker[Session], owner_id: str, conversation_id: str) -> None:
    message_repo = MessageRepository(session_factory)
    user_message, assistant_message = message_repo.create_user_and_assistant(
        conversation_id,
        owner_id,
        content="previous user message",
        client_request_id="00000000-0000-0000-0000-000000000111",
        assistant_model="deepseek-chat",
    )
    message_repo.finalize(
        assistant_message.id,
        owner_id,
        expected_status="pending",
        status="completed",
        content="previous assistant message",
        model="deepseek-chat",
        prompt_tokens=5,
        completion_tokens=7,
        total_tokens=12,
    )


def test_chat_service_completes_turn_persists_response_and_context(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    conversation_repo = ConversationRepository(session_factory)
    llm_run_repo = LLMRunRepository(session_factory)
    fake_llm = FakeLLMClient(
        outcomes=[
            ChatCompletionResult(
                request_id="00000000-0000-0000-0000-000000000222",
                prompt_version="v1",
                model="deepseek-chat",
                message=LLMMessage(role="assistant", content="final answer"),
                finish_reason="stop",
                usage=ChatCompletionUsage(prompt_tokens=11, completion_tokens=13, total_tokens=24),
            )
        ]
    )
    service = _build_service(session_factory, fake_llm)

    with session_factory() as session:
        owner = _create_user(session, email="owner@example.com")
        session.commit()

    conversation = conversation_repo.create(owner.id, "Thread", "deepseek-chat", system_prompt_version="v1")
    _seed_completed_turn(session_factory, owner.id, conversation.id)

    result = service.complete(
        owner.id,
        conversation.id,
        "How is the current project structured?",
        "00000000-0000-0000-0000-000000000333",
    )

    assert result.replayed is False
    assert result.user_message.content == "How is the current project structured?"
    assert result.assistant_message.content == "final answer"
    assert result.assistant_message.status == "completed"
    assert result.llm_run.status == "completed"
    assert result.llm_run.prompt_tokens == 11
    assert result.llm_run.completion_tokens == 13
    assert result.llm_run.total_tokens == 24
    assert result.llm_run.finish_reason == "stop"
    assert len(fake_llm.complete_calls) == 1

    call = fake_llm.complete_calls[0]
    assert call.request_id == "00000000-0000-0000-0000-000000000333"
    assert call.prompt_version == "v1"
    assert call.model == "deepseek-chat"
    assert [message.role for message in call.messages] == ["system", "user", "assistant", "user"]
    assert call.messages[-1].content == "How is the current project structured?"

    with session_factory() as session:
        stored_conversation = session.get(ChatbotConversation, conversation.id)
        stored_run = session.get(ChatbotLLMRun, str(result.llm_run.id))
        assert stored_conversation is not None
        assert stored_conversation.next_sequence == 5
        assert stored_run is not None
        assert stored_run.status == "completed"


def test_chat_service_uses_short_term_memory_for_history(tmp_path, monkeypatch) -> None:
    session_factory = _build_session_factory(tmp_path)
    conversation_repo = ConversationRepository(session_factory)
    fake_llm = FakeLLMClient(
        outcomes=[
            ChatCompletionResult(
                request_id="00000000-0000-0000-0000-000000001111",
                prompt_version="v1",
                model="deepseek-chat",
                message=LLMMessage(role="assistant", content="final answer"),
                finish_reason="stop",
                usage=ChatCompletionUsage(prompt_tokens=11, completion_tokens=13, total_tokens=24),
            )
        ]
    )
    service = _build_service(session_factory, fake_llm)

    class FakeShortTermMemory:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str, str]] = []

        def load_history(self, session, user_id: str, conversation_id: str, *, before_sequence_number: int):
            self.calls.append((user_id, conversation_id, str(before_sequence_number)))
            return (LLMMessage(role="assistant", content="cached assistant"),)

        def refresh_context(self, *args, **kwargs):
            return None

    fake_memory = FakeShortTermMemory()
    service.short_term_memory = fake_memory  # type: ignore[attr-defined]

    with session_factory() as session:
        owner = _create_user(session, email="owner@example.com")
        session.commit()

    conversation = conversation_repo.create(owner.id, "Thread", "deepseek-chat", system_prompt_version="v1")
    _seed_completed_turn(session_factory, owner.id, conversation.id)

    result = service.complete(
        owner.id,
        conversation.id,
        "How is the current project structured?",
        "00000000-0000-0000-0000-000000001222",
    )

    assert result.replayed is False
    assert fake_memory.calls
    assert len(fake_llm.complete_calls) == 1
    assert [message.role for message in fake_llm.complete_calls[0].messages] == ["system", "assistant", "user"]


def test_chat_service_replays_completed_request_and_conflict_detects_payload_mismatch(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    conversation_repo = ConversationRepository(session_factory)
    fake_llm = FakeLLMClient(
        outcomes=[
            ChatCompletionResult(
                request_id="00000000-0000-0000-0000-000000000444",
                prompt_version="v1",
                model="deepseek-chat",
                message=LLMMessage(role="assistant", content="first answer"),
                finish_reason="stop",
                usage=ChatCompletionUsage(prompt_tokens=1, completion_tokens=2, total_tokens=3),
            )
        ]
    )
    service = _build_service(session_factory, fake_llm)

    with session_factory() as session:
        owner = _create_user(session, email="owner@example.com")
        session.commit()

    conversation = conversation_repo.create(owner.id, "Thread", "deepseek-chat", system_prompt_version="v1")

    first = service.complete(
        owner.id,
        conversation.id,
        "What is the deployment flow?",
        "00000000-0000-0000-0000-000000000555",
    )
    replay = service.complete(
        owner.id,
        conversation.id,
        "What is the deployment flow?",
        "00000000-0000-0000-0000-000000000555",
    )

    assert first.replayed is False
    assert replay.replayed is True
    assert replay.assistant_message.id == first.assistant_message.id
    assert len(fake_llm.complete_calls) == 1

    with pytest.raises(ChatbotApiError) as exc:
        service.complete(
            owner.id,
            conversation.id,
            "What is a different deployment flow?",
            "00000000-0000-0000-0000-000000000555",
        )
    assert exc.value.code == "CHATBOT_IDEMPOTENCY_CONFLICT"


def test_chat_service_rejects_busy_conversation(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    conversation_repo = ConversationRepository(session_factory)
    llm_run_repo = LLMRunRepository(session_factory)
    fake_llm = FakeLLMClient()
    service = _build_service(session_factory, fake_llm)

    with session_factory() as session:
        owner = _create_user(session, email="owner@example.com")
        session.commit()

    conversation = conversation_repo.create(owner.id, "Thread", "deepseek-chat", system_prompt_version="v1")
    message_repo = MessageRepository(session_factory)
    _, assistant_message = message_repo.create_user_and_assistant(
        conversation.id,
        owner.id,
        content="previous user message",
        client_request_id="00000000-0000-0000-0000-000000000666",
        assistant_model="deepseek-chat",
    )
    llm_run_repo.create(
        request_id="00000000-0000-0000-0000-000000000667",
        user_id=owner.id,
        conversation_id=conversation.id,
        message_id=assistant_message.id,
        provider="deepseek",
        model="deepseek-chat",
        prompt_version="v1",
    )

    with pytest.raises(ChatbotApiError) as exc:
        service.complete(
            owner.id,
            conversation.id,
            "New message",
            "00000000-0000-0000-0000-000000000668",
        )
    assert exc.value.code == "CHATBOT_CONVERSATION_BUSY"
    assert fake_llm.complete_calls == []
