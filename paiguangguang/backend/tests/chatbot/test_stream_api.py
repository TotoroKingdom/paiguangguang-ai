from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.llm.provider import ChatCompletionRequest, ChatCompletionUsage, LLMStreamEvent
from app.chatbot.repositories.conversation_repository import ConversationRepository
from app.chatbot.services.chat_service import ChatService
from app.chatbot.services.stream_service import ChatStreamService, get_chat_stream_service
from app.core.config import Settings
from app.db.base import Base
from app.db.models import User
from app.db.session import get_db_session
from app.main import app as fastapi_app
from app.services.auth import AuthService, get_auth_service


def _build_session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_engine(f"sqlite+pysqlite:///{(tmp_path / f'{uuid4()}.sqlite3').as_posix()}", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


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


def _build_test_app(session: Session, auth_service: AuthService, stream_service) -> object:
    app = fastapi_app
    app.dependency_overrides.clear()

    def override_db_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_chat_stream_service] = lambda: stream_service
    return app


def _create_user(session: Session, auth_service: AuthService, *, email: str) -> User:
    return auth_service.create_user(
        session,
        email=email,
        display_name=email.split("@")[0].title(),
        password="Secret123!Strong",
        is_active=True,
    )


def test_chat_stream_api_returns_sse_and_replays_terminal_turn(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-for-chatbot-api-strong")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")

    session_factory = _build_session_factory(tmp_path)
    session = session_factory()
    auth_service = AuthService()
    conversation_repo = ConversationRepository(session_factory)
    settings = Settings(
        chatbot_default_model="deepseek-chat",
        chatbot_allowed_models=["deepseek-chat"],
        chatbot_message_max_chars=4000,
        chatbot_recent_message_limit=20,
    )
    fake_llm = FakeLLMClient(
        outcomes=[
            [
                LLMStreamEvent(
                    kind="delta",
                    request_id="00000000-0000-0000-0000-000000001234",
                    prompt_version="v1",
                    model="deepseek-chat",
                    content="架构",
                ),
                LLMStreamEvent(
                    kind="completed",
                    request_id="00000000-0000-0000-0000-000000001234",
                    prompt_version="v1",
                    model="deepseek-chat",
                    content="架构选择",
                    finish_reason="stop",
                    usage=ChatCompletionUsage(prompt_tokens=1, completion_tokens=2, total_tokens=3),
                ),
            ]
        ]
    )
    chat_service = ChatService(session_factory=session_factory, llm_client=fake_llm, settings=settings)
    stream_service = ChatStreamService(chat_service=chat_service)

    with session_factory() as seed_session:
        owner = _create_user(seed_session, auth_service, email="owner@example.com")
        seed_session.commit()

    conversation = conversation_repo.create(owner.id, "Thread", "deepseek-chat", system_prompt_version="v1")

    app = _build_test_app(session, auth_service, stream_service)
    client = TestClient(app)

    try:
        login_response = client.post("/api/v1/auth/login", json={"email": owner.email, "password": "Secret123!Strong"})
        headers = {
            "Authorization": f"Bearer {login_response.json()['data']['access_token']}",
            "Idempotency-Key": "00000000-0000-0000-0000-000000001234",
            "Accept": "text/event-stream",
        }

        response = client.post(
            f"/api/v1/chatbot/conversations/{conversation.id}/messages",
            headers=headers,
            json={
                "content": "请总结当前架构选择",
                "client_request_id": "00000000-0000-0000-0000-000000001234",
            },
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        body = response.text
        assert "event: message.created" in body
        assert "event: stream.end" in body
        assert '"replayed":false' in body
        assert len(fake_llm.stream_calls) == 1

        replay_response = client.post(
            f"/api/v1/chatbot/conversations/{conversation.id}/messages",
            headers=headers,
            json={
                "content": "请总结当前架构选择",
                "client_request_id": "00000000-0000-0000-0000-000000001234",
            },
        )
        assert replay_response.status_code == 200
        assert '"replayed":true' in replay_response.text
        assert len(fake_llm.stream_calls) == 1
    finally:
        app.dependency_overrides.clear()
        session.close()
