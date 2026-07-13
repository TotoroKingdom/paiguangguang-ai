from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.main import app as fastapi_app
from app.chatbot.repositories.message_repository import MessageRepository
from app.chatbot.repositories.memory_repository import MemoryRepository
from app.chatbot.services.concurrency_service import ConcurrencyService
from app.db.base import Base
from app.db.models import User
from app.db.session import get_db_session
from app.services.auth import AuthService, get_auth_service
from app.chatbot.services.memory_service import MemoryService
from app.chatbot.services.memory_service import get_memory_service
from app.services.rag_cache import build_authorized_cache_key
from app.storage.rag_search import RagSearchAccessContext


def _build_session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_engine(f"sqlite+pysqlite:///{(tmp_path / f'{uuid4()}.sqlite3').as_posix()}", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def _build_test_app(session: Session, auth_service: AuthService, session_factory: sessionmaker[Session]) -> FastAPI:
    app = fastapi_app
    app.dependency_overrides.clear()

    def override_db_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_memory_service] = lambda: MemoryService(
        session_factory=session_factory,
        settings=auth_service.settings,
    )
    return app


def _create_user(session: Session, auth_service: AuthService, *, email: str) -> User:
    return auth_service.create_user(
        session,
        email=email,
        display_name=email.split("@")[0].title(),
        password="Secret123!",
        is_active=True,
    )


def test_authorization_matrix_blocks_foreign_access_and_scopes_chroma_redis(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-for-chatbot-matrix")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")

    session_factory = _build_session_factory(tmp_path)
    session = session_factory()
    auth_service = AuthService()
    owner = _create_user(session, auth_service, email="owner@example.com")
    foreign = _create_user(session, auth_service, email="foreign@example.com")

    app = _build_test_app(session, auth_service, session_factory)
    client = TestClient(app)

    try:
        owner_login = client.post("/api/v1/auth/login", json={"email": owner.email, "password": "Secret123!"})
        foreign_login = client.post("/api/v1/auth/login", json={"email": foreign.email, "password": "Secret123!"})
        owner_headers = {"Authorization": f"Bearer {owner_login.json()['data']['access_token']}"}
        foreign_headers = {"Authorization": f"Bearer {foreign_login.json()['data']['access_token']}"}

        conversation_response = client.post(
            "/api/v1/chatbot/conversations",
            headers=owner_headers,
            json={"title": "Owner thread"},
        )
        assert conversation_response.status_code == 201
        conversation_id = conversation_response.json()["data"]["id"]

        message_repo = MessageRepository(session_factory)
        _, assistant_message = message_repo.create_user_and_assistant(
            conversation_id,
            owner.id,
            content="seed message",
            client_request_id="00000000-0000-0000-0000-000000000701",
            assistant_model="deepseek-chat",
        )
        message_repo.finalize(
            assistant_message.id,
            owner.id,
            expected_status="pending",
            status="completed",
            content="assistant reply",
            model="deepseek-chat",
        )

        memory_repo = MemoryRepository(session_factory)
        memory = memory_repo.create(
            owner.id,
            memory_type="fact",
            content="owner-only memory",
            normalized_hash="owner-only-memory",
            conversation_id=conversation_id,
            status="active",
            embedding_status="indexed",
        )

        foreign_conversation = client.get(f"/api/v1/chatbot/conversations/{conversation_id}", headers=foreign_headers)
        assert foreign_conversation.status_code == 404
        assert foreign_conversation.json()["error"]["code"] == "CHATBOT_CONVERSATION_NOT_FOUND"

        foreign_messages = client.get(
            f"/api/v1/chatbot/conversations/{conversation_id}/messages",
            headers=foreign_headers,
        )
        assert foreign_messages.status_code == 404
        assert foreign_messages.json()["error"]["code"] == "CHATBOT_CONVERSATION_NOT_FOUND"

        foreign_memory = client.get(f"/api/v1/chatbot/memories/{memory.id}", headers=foreign_headers)
        assert foreign_memory.status_code == 404
        assert foreign_memory.json()["error"]["code"] == "CHATBOT_MEMORY_NOT_FOUND"

        owner_context = RagSearchAccessContext(
            user_id=owner.id,
            workspace_id="workspace-1",
            allowed_permission_scopes=("rag.query",),
        )
        foreign_context = RagSearchAccessContext(
            user_id=foreign.id,
            workspace_id="workspace-1",
            allowed_permission_scopes=("rag.query",),
        )
        owner_cache_key = build_authorized_cache_key(
            "rag:answer",
            access_context=owner_context,
            knowledge_base_version="kb-v1",
            retrieval_strategy_version="strategy-v1",
            model_version="model-v1",
            payload={"conversation_id": conversation_id},
        )
        foreign_cache_key = build_authorized_cache_key(
            "rag:answer",
            access_context=foreign_context,
            knowledge_base_version="kb-v1",
            retrieval_strategy_version="strategy-v1",
            model_version="model-v1",
            payload={"conversation_id": conversation_id},
        )
        assert owner_cache_key != foreign_cache_key
        assert ConcurrencyService.build_key(conversation_id, owner.id) != ConcurrencyService.build_key(
            conversation_id,
            foreign.id,
        )
    finally:
        app.dependency_overrides.clear()
        session.close()
