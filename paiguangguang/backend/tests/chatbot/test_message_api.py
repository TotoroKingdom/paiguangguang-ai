from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.models.conversation import ChatbotConversation
from app.chatbot.repositories.conversation_repository import ConversationRepository
from app.chatbot.repositories.message_repository import MessageRepository
from app.chatbot.services.conversation_service import ConversationService
from app.chatbot.services.message_service import get_message_service
from app.db.base import Base
from app.db.models import User
from app.db.session import get_db_session
from app.main import app as fastapi_app
from app.services.auth import AuthService, get_auth_service


def _build_session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_engine(f"sqlite+pysqlite:///{(tmp_path / f'{uuid4()}.sqlite3').as_posix()}", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def _build_test_app(session: Session, auth_service: AuthService):
    app = fastapi_app
    app.dependency_overrides.clear()

    def override_db_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_message_service] = get_message_service
    return app


def _create_user(session: Session, auth_service: AuthService, *, email: str) -> User:
    return auth_service.create_user(
        session,
        email=email,
        display_name=email.split("@")[0].title(),
        password="Secret123!Strong",
        is_active=True,
    )


def test_message_api_lists_messages_with_cursor_and_owner_filter(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-for-chatbot-api-strong")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")

    session_factory = _build_session_factory(tmp_path)
    session = session_factory()
    auth_service = AuthService()
    conversation_repo = ConversationRepository(session_factory)
    message_repo = MessageRepository(session_factory)
    conversation_service = ConversationService()

    with session_factory() as seed_session:
        owner = _create_user(seed_session, auth_service, email="owner@example.com")
        foreign = _create_user(seed_session, auth_service, email="foreign@example.com")
        seed_session.commit()

    conversation = conversation_repo.create(owner.id, "Thread", "deepseek-chat")
    for index in range(3):
        _, assistant_message = message_repo.create_user_and_assistant(
            conversation.id,
            owner.id,
            content=f"message-{index}",
            client_request_id=f"00000000-0000-0000-0000-00000000{index:04d}",
            assistant_model="deepseek-chat",
        )
        if index == 0:
            message_repo.checkpoint(
                assistant_message.id,
                owner.id,
                expected_status="pending",
                content="partial",
            )
            message_repo.finalize(
                assistant_message.id,
                owner.id,
                expected_status="streaming",
                status="failed",
                content="partial",
                error_code="CHATBOT_LLM_TIMEOUT",
            )

    app = _build_test_app(session, auth_service)
    client = TestClient(app)

    try:
        openapi_paths = app.openapi()["paths"]
        assert "/api/v1/chatbot/conversations/{conversation_id}/messages" in openapi_paths

        owner_login = client.post("/api/v1/auth/login", json={"email": owner.email, "password": "Secret123!Strong"})
        foreign_login = client.post("/api/v1/auth/login", json={"email": foreign.email, "password": "Secret123!Strong"})
        owner_headers = {"Authorization": f"Bearer {owner_login.json()['data']['access_token']}"}
        foreign_headers = {"Authorization": f"Bearer {foreign_login.json()['data']['access_token']}"}

        first_page = client.get(
            f"/api/v1/chatbot/conversations/{conversation.id}/messages?limit=2",
            headers=owner_headers,
        )
        assert first_page.status_code == 200
        first_payload = first_page.json()["data"]
        assert [item["sequence_number"] for item in first_payload["items"]] == [5, 6]
        assert first_payload["items"][0]["status"] == "completed"
        assert first_payload["items"][1]["status"] == "pending"
        assert "user_id" not in first_payload["items"][0]
        assert first_payload["has_more"] is True

        second_page = client.get(
            f"/api/v1/chatbot/conversations/{conversation.id}/messages?limit=2&before={first_payload['next_cursor']}",
            headers=owner_headers,
        )
        assert second_page.status_code == 200
        assert [item["sequence_number"] for item in second_page.json()["data"]["items"]] == [3, 4]

        invalid_cursor_response = client.get(
            f"/api/v1/chatbot/conversations/{conversation.id}/messages?before=not-a-cursor",
            headers=owner_headers,
        )
        assert invalid_cursor_response.status_code == 400
        assert invalid_cursor_response.json()["error"]["code"] == "CHATBOT_INVALID_CURSOR"

        foreign_response = client.get(
            f"/api/v1/chatbot/conversations/{conversation.id}/messages",
            headers=foreign_headers,
        )
        assert foreign_response.status_code == 404
        assert foreign_response.json()["error"]["code"] == "CHATBOT_CONVERSATION_NOT_FOUND"
    finally:
        app.dependency_overrides.clear()
        session.close()


def test_message_api_rejects_missing_auth_and_deleted_conversation(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-for-chatbot-api-strong")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")

    session_factory = _build_session_factory(tmp_path)
    session = session_factory()
    auth_service = AuthService()
    conversation_repo = ConversationRepository(session_factory)
    message_repo = MessageRepository(session_factory)

    with session_factory() as seed_session:
        owner = _create_user(seed_session, auth_service, email="owner@example.com")
        seed_session.commit()

    conversation = conversation_repo.create(owner.id, "Thread", "deepseek-chat")
    message_repo.create_user_and_assistant(
        conversation.id,
        owner.id,
        content="hello",
        client_request_id="00000000-0000-0000-0000-000000009999",
        assistant_model="deepseek-chat",
    )
    with session_factory() as delete_session:
        ConversationService().delete_conversation(delete_session, owner.id, conversation.id)

    app = _build_test_app(session, auth_service)
    client = TestClient(app)

    try:
        no_auth_response = client.get(f"/api/v1/chatbot/conversations/{conversation.id}/messages")
        assert no_auth_response.status_code == 401
        assert no_auth_response.json()["error"]["code"] == "AUTHENTICATION_ERROR"

        login_response = client.post("/api/v1/auth/login", json={"email": owner.email, "password": "Secret123!Strong"})
        headers = {"Authorization": f"Bearer {login_response.json()['data']['access_token']}"}
        deleted_response = client.get(f"/api/v1/chatbot/conversations/{conversation.id}/messages", headers=headers)
        assert deleted_response.status_code == 404
        assert deleted_response.json()["error"]["code"] == "CHATBOT_CONVERSATION_NOT_FOUND"
    finally:
        app.dependency_overrides.clear()
        session.close()
