from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.errors import ChatbotApiError
from app.chatbot.llm.provider import ChatCompletionRequest, ChatCompletionResult, ChatCompletionUsage, LLMMessage
from app.chatbot.repositories.conversation_repository import ConversationRepository
from app.chatbot.services.chat_service import ChatService
from app.chatbot.api.dependencies import get_chat_stream_service
from app.db.base import Base
from app.db.models import User
from app.db.session import get_db_session
from app.main import app as fastapi_app
from app.services.auth import AuthService, get_auth_service


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


def _create_user(session: Session, auth_service: AuthService, *, email: str) -> User:
    return auth_service.create_user(
        session,
        email=email,
        display_name=email.split("@")[0].title(),
        password="Secret123!",
        is_active=True,
    )


def _build_service(session_factory: sessionmaker[Session], llm_client: FakeLLMClient | None = None) -> ChatService:
    return ChatService(
        session_factory=session_factory,
        llm_client=llm_client,
        settings=None,
    )


def test_chat_service_rejects_same_idempotency_key_with_different_payload(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-for-chatbot-idempotency")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")

    session_factory = _build_session_factory(tmp_path)
    conversation_repo = ConversationRepository(session_factory)
    fake_llm = FakeLLMClient(
        outcomes=[
            ChatCompletionResult(
                request_id="00000000-0000-0000-0000-000000000811",
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
        owner = _create_user(session, AuthService(), email="owner@example.com")
        session.commit()

    conversation = conversation_repo.create(owner.id, "Thread", "deepseek-chat", system_prompt_version="v1")

    first = service.complete(
        owner.id,
        conversation.id,
        "What is the deployment flow?",
        "00000000-0000-0000-0000-000000000810",
    )
    replay = service.complete(
        owner.id,
        conversation.id,
        "What is the deployment flow?",
        "00000000-0000-0000-0000-000000000810",
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
            "00000000-0000-0000-0000-000000000810",
        )
    assert exc.value.code == "CHATBOT_IDEMPOTENCY_CONFLICT"


def test_message_endpoint_rejects_header_body_id_mismatch(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-for-chatbot-idempotency-api")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")

    session_factory = _build_session_factory(tmp_path)
    session = session_factory()
    auth_service = AuthService()
    owner = _create_user(session, auth_service, email="owner@example.com")

    app = fastapi_app
    app.dependency_overrides.clear()

    def override_db_session():
        yield session

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_chat_stream_service] = lambda: object()

    client = TestClient(app)

    try:
        login = client.post("/api/v1/auth/login", json={"email": owner.email, "password": "Secret123!"})
        headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}
        response = client.post(
            "/api/v1/chatbot/conversations/00000000-0000-0000-0000-000000000999/messages",
            headers={**headers, "Idempotency-Key": "00000000-0000-0000-0000-000000001111"},
            json={
                "content": "Hello world",
                "client_request_id": "00000000-0000-0000-0000-000000001112",
            },
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "CHATBOT_IDEMPOTENCY_KEY_MISMATCH"
    finally:
        app.dependency_overrides.clear()
        session.close()
