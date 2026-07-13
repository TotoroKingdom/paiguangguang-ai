from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass, field
from pathlib import Path
from queue import Queue
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.llm.provider import ChatCompletionRequest, ChatCompletionResult, ChatCompletionUsage, LLMMessage, LLMStreamEvent
from app.chatbot.models.conversation import ChatbotConversation
from app.chatbot.repositories.conversation_repository import ConversationRepository
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
    stream_outcomes: list[list[LLMStreamEvent] | Exception] = field(default_factory=list)
    stream_calls: list[ChatCompletionRequest] = field(default_factory=list)

    def stream(self, request: ChatCompletionRequest):
        self.stream_calls.append(request)
        if not self.stream_outcomes:
            raise AssertionError("Unexpected stream() call")
        outcome = self.stream_outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        yield from outcome

    def complete(self, request: ChatCompletionRequest) -> ChatCompletionResult:
        raise AssertionError("Unexpected complete() call")

    def close(self) -> None:
        return None


def _build_session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_engine(f"sqlite+pysqlite:///{(tmp_path / f'{uuid4()}.sqlite3').as_posix()}", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def _build_settings() -> Settings:
    return Settings(
        chatbot_default_model="deepseek-chat",
        chatbot_allowed_models=["deepseek-chat"],
        chatbot_message_max_chars=4000,
        chatbot_recent_message_limit=20,
    )


def _create_user(session: Session, auth_service: AuthService, *, email: str) -> User:
    return auth_service.create_user(
        session,
        email=email,
        display_name=email.split("@")[0].title(),
        password="Secret123!Strong",
        is_active=True,
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


def test_chatbot_failure_matrix_auth_cursor_and_ownership_guards(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-for-chatbot-failure-matrix")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")

    session_factory = _build_session_factory(tmp_path)
    session = session_factory()
    auth_service = AuthService()
    conversation_repo = ConversationRepository(session_factory)
    settings = _build_settings()
    fake_llm = FakeLLMClient()
    chat_service = ChatService(session_factory=session_factory, llm_client=fake_llm, settings=settings)
    stream_service = ChatStreamService(chat_service=chat_service, settings=settings)

    with session_factory() as seed_session:
        owner = _create_user(seed_session, auth_service, email="owner@example.com")
        foreign = _create_user(seed_session, auth_service, email="foreign@example.com")
        seed_session.commit()

    conversation = conversation_repo.create(owner.id, "Thread", "deepseek-chat", system_prompt_version="v1")
    app = _build_test_app(session, auth_service, stream_service)
    client = TestClient(app)

    try:
        assert client.post("/api/v1/chatbot/conversations", json={"title": "no auth"}).status_code == 401

        owner_token = _login(client, owner.email)
        foreign_token = _login(client, foreign.email)
        owner_headers = {"Authorization": f"Bearer {owner_token}"}
        foreign_headers = {"Authorization": f"Bearer {foreign_token}"}

        invalid_cursor = client.get("/api/v1/chatbot/conversations?cursor=not-a-cursor", headers=owner_headers)
        assert invalid_cursor.status_code == 400
        assert invalid_cursor.json()["error"]["code"] == "CHATBOT_INVALID_CURSOR"

        foreign_detail = client.get(f"/api/v1/chatbot/conversations/{conversation.id}", headers=foreign_headers)
        assert foreign_detail.status_code == 404
        assert foreign_detail.json()["error"]["code"] == "CHATBOT_CONVERSATION_NOT_FOUND"

        missing_messages = client.get(f"/api/v1/chatbot/conversations/{conversation.id}/messages", headers=foreign_headers)
        assert missing_messages.status_code == 404
        assert missing_messages.json()["error"]["code"] == "CHATBOT_CONVERSATION_NOT_FOUND"
    finally:
        app.dependency_overrides.clear()
        session.close()


def test_chatbot_failure_matrix_rejects_idempotency_conflicts_and_non_latest_regenerate(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-for-chatbot-failure-matrix")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")

    session_factory = _build_session_factory(tmp_path)
    session = session_factory()
    auth_service = AuthService()
    conversation_repo = ConversationRepository(session_factory)
    settings = _build_settings()
    fake_llm = FakeLLMClient(
        stream_outcomes=[
            [
                LLMStreamEvent(
                    kind="delta",
                    request_id="00000000-0000-0000-0000-000000003001",
                    prompt_version="v1",
                    model="deepseek-chat",
                    content="first answer",
                ),
                LLMStreamEvent(
                    kind="completed",
                    request_id="00000000-0000-0000-0000-000000003001",
                    prompt_version="v1",
                    model="deepseek-chat",
                    content="first answer",
                    finish_reason="stop",
                    usage=ChatCompletionUsage(prompt_tokens=2, completion_tokens=3, total_tokens=5),
                ),
            ],
            [
                LLMStreamEvent(
                    kind="delta",
                    request_id="00000000-0000-0000-0000-000000003002",
                    prompt_version="v1",
                    model="deepseek-chat",
                    content="second answer",
                ),
                LLMStreamEvent(
                    kind="completed",
                    request_id="00000000-0000-0000-0000-000000003002",
                    prompt_version="v1",
                    model="deepseek-chat",
                    content="second answer",
                    finish_reason="stop",
                    usage=ChatCompletionUsage(prompt_tokens=2, completion_tokens=3, total_tokens=5),
                ),
            ],
            [
                LLMStreamEvent(
                    kind="delta",
                    request_id="00000000-0000-0000-0000-000000003003",
                    prompt_version="v1",
                    model="deepseek-chat",
                    content="later turn",
                ),
                LLMStreamEvent(
                    kind="completed",
                    request_id="00000000-0000-0000-0000-000000003003",
                    prompt_version="v1",
                    model="deepseek-chat",
                    content="later turn",
                    finish_reason="stop",
                    usage=ChatCompletionUsage(prompt_tokens=2, completion_tokens=3, total_tokens=5),
                ),
            ],
        ]
    )
    chat_service = ChatService(session_factory=session_factory, llm_client=fake_llm, settings=settings)
    cancellation_service = CancellationService(settings=settings)
    stream_service = ChatStreamService(chat_service=chat_service, cancellation_service=cancellation_service, settings=settings)

    with session_factory() as seed_session:
        owner = _create_user(seed_session, auth_service, email="owner@example.com")
        seed_session.commit()

    conversation = conversation_repo.create(owner.id, "Thread", "deepseek-chat", system_prompt_version="v1")
    app = _build_test_app(session, auth_service, stream_service)
    client = TestClient(app)

    try:
        token = _login(client, owner.email)
        assert client.post("/api/v1/chatbot/conversations", json={"title": "no auth"}).status_code == 401

        with session_factory() as tx:
            conversation_row = tx.get(ChatbotConversation, conversation.id)
            assert conversation_row is not None
            accepted = chat_service._accept_turn(
                tx,
                user_id=owner.id,
                conversation=conversation_row,
                content="Cancel first so retry is legal",
                client_request_id="00000000-0000-0000-0000-000000003100",
            )
            tx.commit()

        cancellation_service.request_stop(accepted.conversation_id, accepted.assistant_message_id)
        queue: Queue = Queue()
        stream_service._produce_stream_events(
            queue,
            accepted,
            owner.id,
            chat_service._build_request(accepted, "Cancel first so retry is legal"),
            "00000000-0000-0000-0000-000000003000",
        )
        cancelled_events = []
        while True:
            item = queue.get()
            if item is None:
                break
            cancelled_events.append(item)
        assert [event.event for event in cancelled_events] == ["message.cancelled", "usage.updated", "stream.end"]

        conflict = client.post(
            f"/api/v1/chatbot/conversations/{conversation.id}/messages",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "text/event-stream",
                "Idempotency-Key": "00000000-0000-0000-0000-000000003100",
            },
            json={
                "content": "How does the matrix behave differently?",
                "client_request_id": "00000000-0000-0000-0000-000000003100",
            },
        )
        assert conflict.status_code == 409
        assert conflict.json()["error"]["code"] == "CHATBOT_IDEMPOTENCY_CONFLICT"

        retry_events = list(
            stream_service.stream_retry(
                owner.id,
                conversation.id,
                accepted.assistant_message_id,
                "00000000-0000-0000-0000-000000003200",
            )
        )
        assert retry_events[-1].event == "stream.end"
        retry_assistant_message_id = str(retry_events[0].data.assistant_message_id)

        later_message = client.post(
            f"/api/v1/chatbot/conversations/{conversation.id}/messages",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "text/event-stream",
                "Idempotency-Key": "00000000-0000-0000-0000-000000003300",
            },
            json={
                "content": "A later user turn",
                "client_request_id": "00000000-0000-0000-0000-000000003300",
            },
        )
        assert later_message.status_code == 200
        assert len(fake_llm.stream_calls) == 3

        regenerate = client.post(
            f"/api/v1/chatbot/conversations/{conversation.id}/messages/{retry_assistant_message_id}/regenerate",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "text/event-stream",
                "Idempotency-Key": "00000000-0000-0000-0000-000000003400",
            },
            json={"client_request_id": "00000000-0000-0000-0000-000000003400"},
        )
        assert regenerate.status_code == 409
        assert regenerate.json()["error"]["code"] == "CHATBOT_REGENERATE_NOT_LATEST_TURN"
    finally:
        app.dependency_overrides.clear()
        session.close()
