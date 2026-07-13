from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.errors import ChatbotApiError
from app.chatbot.llm.exceptions import LLMTimeoutError
from app.chatbot.llm.provider import ChatCompletionRequest, ChatCompletionUsage, LLMMessage, LLMStreamEvent
from app.chatbot.models.conversation import ChatbotConversation
from app.chatbot.models.llm_run import ChatbotLLMRun
from app.chatbot.repositories.conversation_repository import ConversationRepository
from app.chatbot.repositories.llm_run_repository import LLMRunRepository
from app.chatbot.repositories.message_repository import MessageRepository
from app.chatbot.schemas.stream import ChatStreamEvent
from app.chatbot.services.chat_service import ChatService
from app.chatbot.services.stream_service import ChatStreamService
from app.core.config import Settings
from app.db.base import Base
from app.db.models import User


@dataclass
class FakeLLMClient:
    outcomes: list[object] = field(default_factory=list)
    stream_calls: list[ChatCompletionRequest] = field(default_factory=list)

    def stream(self, request: ChatCompletionRequest):
        self.stream_calls.append(request)
        if not self.outcomes:
            raise AssertionError("Unexpected LLM call")
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        yield from outcome

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


def _build_service(session_factory: sessionmaker[Session], llm_client: FakeLLMClient | None = None) -> ChatStreamService:
    chat_service = ChatService(
        session_factory=session_factory,
        llm_client=llm_client,
        settings=Settings(
            chatbot_default_model="deepseek-chat",
            chatbot_allowed_models=["deepseek-chat"],
            chatbot_message_max_chars=4000,
            chatbot_recent_message_limit=20,
        ),
    )
    return ChatStreamService(chat_service=chat_service)


def test_chat_stream_service_emits_created_delta_completed_usage_and_end(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    conversation_repo = ConversationRepository(session_factory)
    fake_llm = FakeLLMClient(
        outcomes=[
            [
                LLMStreamEvent(
                    kind="delta",
                    request_id="00000000-0000-0000-0000-000000000333",
                    prompt_version="v1",
                    model="deepseek-chat",
                    content="Hello ",
                ),
                LLMStreamEvent(
                    kind="delta",
                    request_id="00000000-0000-0000-0000-000000000333",
                    prompt_version="v1",
                    model="deepseek-chat",
                    content="world",
                ),
                LLMStreamEvent(
                    kind="usage",
                    request_id="00000000-0000-0000-0000-000000000333",
                    prompt_version="v1",
                    model="deepseek-chat",
                    usage=ChatCompletionUsage(prompt_tokens=11, completion_tokens=13, total_tokens=24),
                ),
                LLMStreamEvent(
                    kind="completed",
                    request_id="00000000-0000-0000-0000-000000000333",
                    prompt_version="v1",
                    model="deepseek-chat",
                    content="Hello world",
                    finish_reason="stop",
                    usage=ChatCompletionUsage(prompt_tokens=11, completion_tokens=13, total_tokens=24),
                ),
            ]
        ]
    )
    service = _build_service(session_factory, fake_llm)

    with session_factory() as session:
        owner = _create_user(session, email="owner@example.com")
        session.commit()

    conversation = conversation_repo.create(owner.id, "Thread", "deepseek-chat", system_prompt_version="v1")

    events = list(
        service.stream_completion(
            owner.id,
            conversation.id,
            "How is the current project structured?",
            "00000000-0000-0000-0000-000000000333",
        )
    )

    assert [event.event for event in events] == [
        "message.created",
        "message.delta",
        "message.delta",
        "message.completed",
        "usage.updated",
        "stream.end",
    ]
    assert all(isinstance(event, ChatStreamEvent) for event in events)

    created = events[0].data
    assert created.replayed is False
    assert created.user_message.content == "How is the current project structured?"
    assert created.assistant_message.status == "pending"

    assert events[1].data.delta == "Hello "
    assert events[1].data.content_length == 6
    assert events[2].data.content_length == 11

    completed = events[3].data
    assert completed.message.status == "completed"
    assert completed.message.content == "Hello world"
    assert completed.finish_reason == "stop"

    usage = events[4].data
    assert usage.prompt_tokens == 11
    assert usage.completion_tokens == 13
    assert usage.total_tokens == 24
    assert usage.source == "provider"

    end = events[5].data
    assert end.final_status == "completed"
    assert len(fake_llm.stream_calls) == 1

    with session_factory() as session:
        stored_conversation = session.get(ChatbotConversation, conversation.id)
        stored_run = session.scalar(select(ChatbotLLMRun).where(ChatbotLLMRun.message_id == str(completed.message.id)))
        assert stored_conversation is not None
        assert stored_conversation.next_sequence == 3
        assert stored_run is not None
        assert stored_run.status == "completed"
        assert stored_run.prompt_tokens == 11
        assert stored_run.total_tokens == 24


def test_chat_stream_service_replays_terminal_turn_without_second_llm_call(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    conversation_repo = ConversationRepository(session_factory)
    fake_llm = FakeLLMClient(
        outcomes=[
            [
                LLMStreamEvent(
                    kind="completed",
                    request_id="00000000-0000-0000-0000-000000000444",
                    prompt_version="v1",
                    model="deepseek-chat",
                    content="first answer",
                    finish_reason="stop",
                    usage=ChatCompletionUsage(prompt_tokens=1, completion_tokens=2, total_tokens=3),
                )
            ]
        ]
    )
    service = _build_service(session_factory, fake_llm)

    with session_factory() as session:
        owner = _create_user(session, email="owner@example.com")
        session.commit()

    conversation = conversation_repo.create(owner.id, "Thread", "deepseek-chat", system_prompt_version="v1")

    first_events = list(
        service.stream_completion(
            owner.id,
            conversation.id,
            "What is the deployment flow?",
            "00000000-0000-0000-0000-000000000444",
        )
    )
    replay_events = list(
        service.stream_completion(
            owner.id,
            conversation.id,
            "What is the deployment flow?",
            "00000000-0000-0000-0000-000000000444",
        )
    )

    assert first_events[0].data.replayed is False
    assert replay_events[0].data.replayed is True
    assert [event.event for event in replay_events] == [
        "message.created",
        "message.completed",
        "usage.updated",
        "stream.end",
    ]
    assert len(fake_llm.stream_calls) == 1


def test_chat_stream_service_rejects_pending_duplicate_request(tmp_path) -> None:
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
    _, assistant_message = message_repo.create_user_and_assistant(
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

    with pytest.raises(ChatbotApiError) as exc:
        list(
            service.stream_completion(
                owner.id,
                conversation.id,
                "Please keep this request pending",
                "00000000-0000-0000-0000-000000000889",
            )
        )

    assert exc.value.code == "CHATBOT_REQUEST_IN_PROGRESS"
    assert fake_llm.stream_calls == []
