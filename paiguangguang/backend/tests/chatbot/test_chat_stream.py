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
from app.chatbot.models.job import ChatbotJob
from app.chatbot.models.message import ChatbotMessage
from app.chatbot.repositories.conversation_repository import ConversationRepository
from app.chatbot.repositories.llm_run_repository import LLMRunRepository
from app.chatbot.repositories.message_repository import MessageRepository
from app.chatbot.schemas.stream import ChatStreamEvent
from app.chatbot.services.chat_service import ChatService
from app.chatbot.services.stream_service import ChatStreamService, _CheckpointTracker
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


def test_chat_stream_service_emits_created_delta_completed_usage_and_end(
    monkeypatch, tmp_path
) -> None:
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
        jobs = list(session.scalars(select(ChatbotJob)))
    assert {job.kind for job in jobs} == {"auto_title", "refresh_conversation_context"}
    assert len(jobs) == 2

    with session_factory() as session:
        stored_conversation = session.get(ChatbotConversation, conversation.id)
        stored_run = session.scalar(select(ChatbotLLMRun).where(ChatbotLLMRun.message_id == str(completed.message.id)))
        assert stored_conversation is not None
        assert stored_conversation.next_sequence == 3
        assert stored_run is not None
        assert stored_run.status == "completed"
        assert stored_run.prompt_tokens == 11
        assert stored_run.total_tokens == 24


def test_chat_stream_throttles_many_small_delta_checkpoints(monkeypatch, tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    conversation_repo = ConversationRepository(session_factory)
    request_id = "00000000-0000-0000-0000-000000000334"
    deltas = [
        LLMStreamEvent(
            kind="delta",
            request_id=request_id,
            prompt_version="v1",
            model="deepseek-chat",
            content="x",
        )
        for _ in range(100)
    ]
    fake_llm = FakeLLMClient(
        outcomes=[
            [
                *deltas,
                LLMStreamEvent(
                    kind="completed",
                    request_id=request_id,
                    prompt_version="v1",
                    model="deepseek-chat",
                    content="x" * 100,
                    finish_reason="stop",
                ),
            ]
        ]
    )
    service = _build_service(session_factory, fake_llm)

    def forbidden_refresh(*args, **kwargs):
        raise AssertionError("summary refresh must not run before terminal SSE")

    monkeypatch.setattr(service, "_refresh_short_term_memory", forbidden_refresh)
    checkpoint_calls = 0
    original = service._checkpoint_partial

    def counted_checkpoint(*args, **kwargs):
        nonlocal checkpoint_calls
        checkpoint_calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(service, "_checkpoint_partial", counted_checkpoint)
    with session_factory() as session:
        owner = _create_user(session, email="checkpoint-owner@example.com")
        session.commit()
    conversation = conversation_repo.create(
        owner.id, "Thread", "deepseek-chat", system_prompt_version="v1"
    )

    events = list(
        service.stream_completion(
            owner.id,
            conversation.id,
            "hello",
            request_id,
        )
    )

    assert checkpoint_calls == 1
    assert events[-1].event == "stream.end"


def test_checkpoint_tracker_uses_time_and_character_thresholds() -> None:
    tracker = _CheckpointTracker(interval_seconds=1.0, chars=512, last_checkpoint_at=10.0)

    assert tracker.should_checkpoint(now=10.0, content_length=1) is True
    tracker.mark(now=10.0, content_length=1)
    assert tracker.should_checkpoint(now=10.5, content_length=101) is False
    assert tracker.should_checkpoint(now=11.0, content_length=101) is True
    tracker.mark(now=11.0, content_length=101)
    assert tracker.should_checkpoint(now=11.1, content_length=613) is True


def test_chat_stream_checkpoints_after_character_threshold_and_finalizes_full_content(
    monkeypatch, tmp_path
) -> None:
    session_factory = _build_session_factory(tmp_path)
    request_id = "00000000-0000-0000-0000-000000000335"
    final_content = "y" * 600
    fake_llm = FakeLLMClient(
        outcomes=[
            [
                *[
                    LLMStreamEvent(
                        kind="delta",
                        request_id=request_id,
                        prompt_version="v1",
                        model="deepseek-chat",
                        content="y",
                    )
                    for _ in range(600)
                ],
                LLMStreamEvent(
                    kind="completed",
                    request_id=request_id,
                    prompt_version="v1",
                    model="deepseek-chat",
                    content=final_content,
                    finish_reason="stop",
                ),
            ]
        ]
    )
    service = _build_service(session_factory, fake_llm)
    checkpoint_calls = 0
    original = service._checkpoint_partial

    def counted_checkpoint(*args, **kwargs):
        nonlocal checkpoint_calls
        checkpoint_calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(service, "_checkpoint_partial", counted_checkpoint)
    with session_factory() as session:
        owner = _create_user(session, email="checkpoint-chars@example.com")
        session.commit()
    conversation = ConversationRepository(session_factory).create(
        owner.id, "Thread", "deepseek-chat", system_prompt_version="v1"
    )

    events = list(
        service.stream_completion(owner.id, conversation.id, "hello", request_id)
    )

    completed = next(event for event in events if event.event == "message.completed")
    with session_factory() as session:
        assistant = session.get(ChatbotMessage, str(completed.data.message.id))
    assert checkpoint_calls >= 2
    assert assistant is not None and assistant.content == final_content


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
    with session_factory() as session:
        jobs = list(session.scalars(select(ChatbotJob)))
    assert {job.kind for job in jobs} == {"auto_title", "refresh_conversation_context"}
    assert len(jobs) == 2


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
