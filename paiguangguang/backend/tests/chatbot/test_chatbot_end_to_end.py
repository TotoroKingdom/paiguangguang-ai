from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass, field
import json
from pathlib import Path
from queue import Queue
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.llm.provider import ChatCompletionRequest, ChatCompletionResult, ChatCompletionUsage, LLMMessage, LLMStreamEvent
from app.chatbot.models.conversation import ChatbotConversation
from app.chatbot.repositories.conversation_repository import ConversationRepository
from app.chatbot.repositories.message_repository import MessageRepository
from app.chatbot.services.chat_service import ChatService
from app.chatbot.services.cancellation_service import CancellationService
from app.chatbot.services.stream_service import ChatStreamService, get_chat_stream_service
from app.core.config import Settings
from app.db.base import Base
from app.db.models import User
from app.db.session import get_db_session
from app.main import app as fastapi_app
from app.services.auth import AuthService, get_auth_service


@dataclass
class FakeLLMClient:
    complete_outcomes: list[ChatCompletionResult | Exception] = field(default_factory=list)
    stream_outcomes: list[list[LLMStreamEvent] | Exception] = field(default_factory=list)
    complete_calls: list[ChatCompletionRequest] = field(default_factory=list)
    stream_calls: list[ChatCompletionRequest] = field(default_factory=list)

    def complete(self, request: ChatCompletionRequest) -> ChatCompletionResult:
        self.complete_calls.append(request)
        if not self.complete_outcomes:
            raise AssertionError("Unexpected complete() call")
        outcome = self.complete_outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def stream(self, request: ChatCompletionRequest):
        self.stream_calls.append(request)
        if not self.stream_outcomes:
            raise AssertionError("Unexpected stream() call")
        outcome = self.stream_outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        yield from outcome

    def close(self) -> None:
        return None


def _build_session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_engine(f"sqlite+pysqlite:///{(tmp_path / f'{uuid4()}.sqlite3').as_posix()}", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def _create_user(session: Session, auth_service: AuthService, *, email: str) -> User:
    return auth_service.create_user(
        session,
        email=email,
        display_name=email.split("@")[0].title(),
        password="Secret123!Strong",
        is_active=True,
    )


def _build_settings() -> Settings:
    return Settings(
        chatbot_default_model="deepseek-chat",
        chatbot_allowed_models=["deepseek-chat"],
        chatbot_message_max_chars=4000,
        chatbot_recent_message_limit=20,
    )


def _build_test_app(session: Session, auth_service: AuthService, stream_service: ChatStreamService) -> FastAPI:
    app = fastapi_app
    app.dependency_overrides.clear()

    def override_db_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_chat_stream_service] = lambda: stream_service
    return app


def _login(client: TestClient, email: str) -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": "Secret123!Strong"})
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


def _parse_sse_events(raw: str) -> list[tuple[str, dict[str, object]]]:
    events: list[tuple[str, dict[str, object]]] = []
    for chunk in raw.strip().split("\n\n"):
        event_name: str | None = None
        data_lines: list[str] = []
        for line in chunk.splitlines():
            if line.startswith("event: "):
                event_name = line.removeprefix("event: ")
            elif line.startswith("data: "):
                data_lines.append(line.removeprefix("data: "))
        if event_name and data_lines:
            payload = json.loads("\n".join(data_lines))
            events.append((event_name, payload))
    return events


def _seed_completed_turn(session_factory: sessionmaker[Session], owner_id: str, conversation_id: str) -> None:
    message_repo = MessageRepository(session_factory)
    _, assistant_message = message_repo.create_user_and_assistant(
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


def test_chatbot_end_to_end_complete_refreshes_context_and_memory_pipeline(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-for-chatbot-e2e")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")

    session_factory = _build_session_factory(tmp_path)
    session = session_factory()
    auth_service = AuthService()
    conversation_repo = ConversationRepository(session_factory)
    fake_llm = FakeLLMClient(
        complete_outcomes=[
            ChatCompletionResult(
                request_id="00000000-0000-0000-0000-000000001001",
                prompt_version="v1",
                model="deepseek-chat",
                message=LLMMessage(role="assistant", content="final answer"),
                finish_reason="stop",
                usage=ChatCompletionUsage(prompt_tokens=11, completion_tokens=13, total_tokens=24),
            )
        ]
    )
    chat_service = ChatService(session_factory=session_factory, llm_client=fake_llm, settings=_build_settings())
    refresh_calls: list[tuple[str, str]] = []
    summary_calls: list[tuple[str, str]] = []
    memory_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    chat_service.short_term_memory.refresh_context = lambda user_id, conversation_id: refresh_calls.append((user_id, conversation_id))
    chat_service.conversation_summary.maybe_generate_summary = lambda user_id, conversation_id: summary_calls.append((user_id, conversation_id))
    chat_service.memory_service = SimpleNamespace(
        submit_completed_turn=lambda *args, **kwargs: memory_calls.append((args, kwargs))
    )

    with session_factory() as seed_session:
        owner = _create_user(seed_session, auth_service, email="owner@example.com")
        seed_session.commit()

    conversation = conversation_repo.create(owner.id, "Thread", "deepseek-chat", system_prompt_version="v1")
    _seed_completed_turn(session_factory, owner.id, conversation.id)

    result = chat_service.complete(
        owner.id,
        conversation.id,
        "How is the current project structured?",
        "00000000-0000-0000-0000-000000001111",
    )

    assert result.replayed is False
    assert result.assistant_message.content == "final answer"
    assert len(fake_llm.complete_calls) == 1
    assert fake_llm.complete_calls[0].messages[-1].content == "How is the current project structured?"
    assert refresh_calls == [(owner.id, conversation.id)]
    assert summary_calls == [(owner.id, conversation.id)]
    assert len(memory_calls) == 1
    assert memory_calls[0][0][0] == owner.id
    assert memory_calls[0][0][1] == conversation.id
    assert memory_calls[0][0][2] == str(result.user_message.id)
    assert memory_calls[0][0][3] == str(result.assistant_message.id)


def test_chatbot_end_to_end_stream_replay_stop_retry_and_regenerate(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-for-chatbot-e2e")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")

    session_factory = _build_session_factory(tmp_path)
    session = session_factory()
    auth_service = AuthService()
    conversation_repo = ConversationRepository(session_factory)
    fake_llm = FakeLLMClient(
        stream_outcomes=[
            [
                LLMStreamEvent(
                    kind="delta",
                    request_id="00000000-0000-0000-0000-000000002001",
                    prompt_version="v1",
                    model="deepseek-chat",
                    content="ignored after cancellation",
                ),
                LLMStreamEvent(
                    kind="completed",
                    request_id="00000000-0000-0000-0000-000000002001",
                    prompt_version="v1",
                    model="deepseek-chat",
                    content="ignored after cancellation",
                    finish_reason="stop",
                    usage=ChatCompletionUsage(prompt_tokens=2, completion_tokens=3, total_tokens=5),
                ),
            ],
            [
                LLMStreamEvent(
                    kind="delta",
                    request_id="00000000-0000-0000-0000-000000002002",
                    prompt_version="v1",
                    model="deepseek-chat",
                    content="retry answer",
                ),
                LLMStreamEvent(
                    kind="completed",
                    request_id="00000000-0000-0000-0000-000000002002",
                    prompt_version="v1",
                    model="deepseek-chat",
                    content="retry answer",
                    finish_reason="stop",
                    usage=ChatCompletionUsage(prompt_tokens=3, completion_tokens=4, total_tokens=7),
                ),
            ],
            [
                LLMStreamEvent(
                    kind="delta",
                    request_id="00000000-0000-0000-0000-000000002003",
                    prompt_version="v1",
                    model="deepseek-chat",
                    content="regenerated answer",
                ),
                LLMStreamEvent(
                    kind="completed",
                    request_id="00000000-0000-0000-0000-000000002003",
                    prompt_version="v1",
                    model="deepseek-chat",
                    content="regenerated answer",
                    finish_reason="stop",
                    usage=ChatCompletionUsage(prompt_tokens=5, completion_tokens=6, total_tokens=11),
                ),
            ],
        ]
    )
    settings = _build_settings()
    chat_service = ChatService(session_factory=session_factory, llm_client=fake_llm, settings=settings)
    refresh_calls: list[tuple[str, str]] = []
    summary_calls: list[tuple[str, str]] = []
    chat_service.short_term_memory.refresh_context = lambda user_id, conversation_id: refresh_calls.append((user_id, conversation_id))
    chat_service.conversation_summary.maybe_generate_summary = lambda user_id, conversation_id: summary_calls.append((user_id, conversation_id))
    cancellation_service = CancellationService(settings=settings)
    stream_service = ChatStreamService(chat_service=chat_service, cancellation_service=cancellation_service, settings=settings)

    with session_factory() as seed_session:
        owner = _create_user(seed_session, auth_service, email="owner@example.com")
        seed_session.commit()

    conversation = conversation_repo.create(owner.id, "Thread", "deepseek-chat", system_prompt_version="v1")
    with session_factory() as tx:
        conversation_row = tx.get(ChatbotConversation, conversation.id)
        assert conversation_row is not None
        accepted = chat_service._accept_turn(
            tx,
            user_id=owner.id,
            conversation=conversation_row,
            content="Please stop, then retry and regenerate",
            client_request_id="00000000-0000-0000-0000-000000002100",
        )
        tx.commit()

    cancellation_service.request_stop(accepted.conversation_id, accepted.assistant_message_id)
    queue: Queue = Queue()
    stream_service._produce_stream_events(
        queue,
        accepted,
        owner.id,
        chat_service._build_request(accepted, "Please stop, then retry and regenerate"),
        "00000000-0000-0000-0000-000000002000",
    )

    cancelled_events = []
    while True:
        item = queue.get()
        if item is None:
            break
        cancelled_events.append(item)

    assert [event.event for event in cancelled_events] == ["message.cancelled", "usage.updated", "stream.end"]
    assert refresh_calls[-1] == (owner.id, conversation.id)

    retry_events = list(
        stream_service.stream_retry(
            owner.id,
            conversation.id,
            accepted.assistant_message_id,
            "00000000-0000-0000-0000-000000002200",
        )
    )
    assert [event.event for event in retry_events] == [
        "message.created",
        "message.delta",
        "message.completed",
        "usage.updated",
        "stream.end",
    ]
    retry_assistant_message_id = str(retry_events[0].data.assistant_message_id)
    assert len(fake_llm.stream_calls) == 2

    regenerate_events = list(
        stream_service.stream_regenerate(
            owner.id,
            conversation.id,
            retry_assistant_message_id,
            "00000000-0000-0000-0000-000000002300",
        )
    )
    assert [event.event for event in regenerate_events] == [
        "message.created",
        "message.delta",
        "message.completed",
        "usage.updated",
        "stream.end",
    ]
    assert len(fake_llm.stream_calls) == 3
    assert refresh_calls
    assert summary_calls
