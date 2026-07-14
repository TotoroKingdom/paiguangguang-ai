from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.models.memory import ChatbotMemory
from app.chatbot.repositories.conversation_repository import ConversationRepository
from app.chatbot.repositories.memory_repository import MemoryRepository
from app.chatbot.services.memory_service import MemoryService, get_memory_service
from app.db.base import Base
from app.db.models import User
from app.db.session import get_db_session
from app.main import app as fastapi_app
from app.services.auth import AuthService, get_auth_service


def _build_session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_engine(f"sqlite+pysqlite:///{(tmp_path / f'{uuid4()}.sqlite3').as_posix()}", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def _build_test_app(session: Session, auth_service: AuthService, memory_service: MemoryService) -> FastAPI:
    app = fastapi_app
    app.dependency_overrides.clear()

    def override_db_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_memory_service] = lambda: memory_service
    return app


def _create_user(session: Session, auth_service: AuthService, *, email: str) -> User:
    return auth_service.create_user(
        session,
        email=email,
        display_name=email.split("@")[0].title(),
        password="Secret123!",
        is_active=True,
    )


def _seed_memory(
    repo: MemoryRepository,
    session_factory: sessionmaker[Session],
    user_id: str,
    *,
    conversation_id: str,
    memory_type: str,
    content: str,
    normalized_hash: str,
    status: str,
    updated_at: datetime,
) -> str:
    record = repo.create(
        user_id,
        memory_type=memory_type,
        content=content,
        normalized_hash=normalized_hash,
        conversation_id=conversation_id,
        status=status,
        confidence=0.9,
        importance=0.7,
        source_message_ids=["00000000-0000-0000-0000-000000000111"],
        embedding_status="pending",
    )
    with session_factory() as session:
        row = session.get(ChatbotMemory, record.id)
        if row is not None:
            row.updated_at = updated_at
            session.commit()
    return record.id


def test_memory_api_crud_owner_filter_cursor_and_router_registration(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-for-chatbot-api")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")

    session_factory = _build_session_factory(tmp_path)
    session = session_factory()
    auth_service = AuthService()
    owner = _create_user(session, auth_service, email="owner@example.com")
    foreign = _create_user(session, auth_service, email="foreign@example.com")
    conversation_repo = ConversationRepository(session_factory)
    memory_repo = MemoryRepository(session_factory)

    memory_service = MemoryService(session_factory=session_factory)
    app = _build_test_app(session, auth_service, memory_service)
    client = TestClient(app)

    try:
        assert "/api/v1/chatbot/memories" in app.openapi()["paths"]

        owner_login = client.post("/api/v1/auth/login", json={"email": owner.email, "password": "Secret123!"})
        foreign_login = client.post("/api/v1/auth/login", json={"email": foreign.email, "password": "Secret123!"})
        owner_headers = {"Authorization": f"Bearer {owner_login.json()['data']['access_token']}"}
        foreign_headers = {"Authorization": f"Bearer {foreign_login.json()['data']['access_token']}"}

        owner_conversation = conversation_repo.create(owner.id, "Thread", "deepseek-chat", system_prompt_version="v1")
        foreign_conversation = conversation_repo.create(foreign.id, "Foreign", "deepseek-chat", system_prompt_version="v1")

        active_a = _seed_memory(
            memory_repo,
            session_factory,
            owner.id,
            conversation_id=owner_conversation.id,
            memory_type="project_context",
            content="项目名是星轨",
            normalized_hash="hash-project-a",
            status="active",
            updated_at=datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc),
        )
        active_b = _seed_memory(
            memory_repo,
            session_factory,
            owner.id,
            conversation_id=owner_conversation.id,
            memory_type="goal",
            content="本周完成演示",
            normalized_hash="hash-goal-b",
            status="active",
            updated_at=datetime(2026, 7, 13, 12, 1, tzinfo=timezone.utc),
        )
        candidate = _seed_memory(
            memory_repo,
            session_factory,
            owner.id,
            conversation_id=owner_conversation.id,
            memory_type="preference",
            content="喜欢深色主题",
            normalized_hash="hash-pref-c",
            status="candidate",
            updated_at=datetime(2026, 7, 13, 12, 2, tzinfo=timezone.utc),
        )
        active_pref = _seed_memory(
            memory_repo,
            session_factory,
            owner.id,
            conversation_id=owner_conversation.id,
            memory_type="preference",
            content="喜欢浅色主题",
            normalized_hash="hash-pref-a",
            status="active",
            updated_at=datetime(2026, 7, 13, 12, 1, 30, tzinfo=timezone.utc),
        )
        foreign_active = _seed_memory(
            memory_repo,
            session_factory,
            foreign.id,
            conversation_id=foreign_conversation.id,
            memory_type="project_context",
            content="别人的项目",
            normalized_hash="hash-foreign-a",
            status="active",
            updated_at=datetime(2026, 7, 13, 12, 3, tzinfo=timezone.utc),
        )

        list_response = client.get("/api/v1/chatbot/memories?status=active&limit=1", headers=owner_headers)
        assert list_response.status_code == 200
        list_payload = list_response.json()["data"]
        assert len(list_payload["items"]) == 1
        assert list_payload["has_more"] is True

        next_page = client.get(
            f"/api/v1/chatbot/memories?status=active&limit=1&cursor={list_payload['next_cursor']}",
            headers=owner_headers,
        )
        assert next_page.status_code == 200
        assert len(next_page.json()["data"]["items"]) == 1

        detail_response = client.get(f"/api/v1/chatbot/memories/{active_b}", headers=owner_headers)
        assert detail_response.status_code == 200
        assert detail_response.json()["data"]["id"] == active_b

        update_response = client.patch(
            f"/api/v1/chatbot/memories/{candidate}",
            headers=owner_headers,
            json={"content": "深色主题优先", "status": "candidate", "expires_at": "2026-07-20T12:00:00Z"},
        )
        assert update_response.status_code == 200
        assert update_response.json()["data"]["content"] == "深色主题优先"

        with session_factory() as verification_session:
            updated_row = verification_session.get(ChatbotMemory, candidate)
            assert updated_row is not None
            assert updated_row.embedding_status == "pending"
            assert updated_row.status == "candidate"

        conflict_memory = _seed_memory(
            memory_repo,
            session_factory,
            owner.id,
            conversation_id=owner_conversation.id,
            memory_type="preference",
            content="喜欢暗色主题",
            normalized_hash="hash-pref-d",
            status="candidate",
            updated_at=datetime(2026, 7, 13, 12, 4, tzinfo=timezone.utc),
        )

        conflict_response = client.patch(
            f"/api/v1/chatbot/memories/{conflict_memory}",
            headers=owner_headers,
            json={"status": "active"},
        )
        assert conflict_response.status_code == 409
        assert conflict_response.json()["error"]["code"] == "CHATBOT_MEMORY_CONFLICT"
        assert conflict_response.json()["error"]["details"]["memory_id"] == active_pref

        delete_response = client.delete(f"/api/v1/chatbot/memories/{active_a}", headers=owner_headers)
        assert delete_response.status_code == 200
        assert delete_response.json()["data"]["status"] == "deleted"
        assert delete_response.json()["data"]["cleanup_status"] == "pending"

        foreign_detail = client.get(f"/api/v1/chatbot/memories/{foreign_active}", headers=owner_headers)
        assert foreign_detail.status_code == 404
        assert foreign_detail.json()["error"]["code"] == "CHATBOT_MEMORY_NOT_FOUND"
    finally:
        app.dependency_overrides.clear()
        session.close()


def test_memory_api_rejects_missing_auth_and_invalid_cursor(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-for-chatbot-api")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")

    session_factory = _build_session_factory(tmp_path)
    session = session_factory()
    auth_service = AuthService()
    user = _create_user(session, auth_service, email="owner@example.com")
    conversation_repo = ConversationRepository(session_factory)
    memory_repo = MemoryRepository(session_factory)
    conversation = conversation_repo.create(user.id, "Thread", "deepseek-chat", system_prompt_version="v1")
    _seed_memory(
        memory_repo,
        session_factory,
        user.id,
        conversation_id=conversation.id,
        memory_type="project_context",
        content="项目名是星轨",
        normalized_hash="hash-project-x",
        status="active",
        updated_at=datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc),
    )

    memory_service = MemoryService(session_factory=session_factory)
    app = _build_test_app(session, auth_service, memory_service)
    client = TestClient(app)

    try:
        no_auth_response = client.get("/api/v1/chatbot/memories")
        assert no_auth_response.status_code == 401
        assert no_auth_response.json()["error"]["code"] == "AUTHENTICATION_ERROR"

        login_response = client.post("/api/v1/auth/login", json={"email": user.email, "password": "Secret123!"})
        headers = {"Authorization": f"Bearer {login_response.json()['data']['access_token']}"}

        invalid_cursor_response = client.get("/api/v1/chatbot/memories?cursor=not-a-cursor", headers=headers)
        assert invalid_cursor_response.status_code == 400
        assert invalid_cursor_response.json()["error"]["code"] == "CHATBOT_INVALID_CURSOR"
    finally:
        app.dependency_overrides.clear()
        session.close()
