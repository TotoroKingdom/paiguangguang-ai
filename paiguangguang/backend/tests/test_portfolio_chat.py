from __future__ import annotations

from collections.abc import Generator

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.main import app as fastapi_app
from app.db.base import Base
from app.db.models import User
from app.db.session import get_db_session
from app.services.auth import AuthService, get_auth_service


def _build_test_app(session: Session, auth_service: AuthService) -> FastAPI:
    app = fastapi_app
    app.dependency_overrides.clear()

    def override_db_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    return app


def _create_user(session: Session, auth_service: AuthService) -> User:
    return auth_service.create_user(
        session,
        email="admin@example.com",
        display_name="Admin User",
        password="Secret123!",
        is_active=True,
    )


def _login(client: TestClient, email: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


def test_legacy_portfolio_chat_requires_jwt_and_is_deprecated(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-for-task18-login-tests")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")

    legacy_db_path = tmp_path / "legacy-chat.sqlite3"
    engine = create_engine(f"sqlite+pysqlite:///{legacy_db_path.as_posix()}")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_factory()
    auth_service = AuthService()
    _create_user(session, auth_service)

    app = _build_test_app(session, auth_service)
    client = TestClient(app)

    try:
        unauthenticated = client.post("/api/v1/chat/chat", json={"message": "What is this project?"})
        assert unauthenticated.status_code == 401
        assert unauthenticated.json()["error"]["code"] == "AUTHENTICATION_ERROR"

        access_token = _login(client, "admin@example.com", "Secret123!")
        response = client.post(
            "/api/v1/chat/chat",
            json={"message": "What is this project?"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 410
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "CHATBOT_LEGACY_CHAT_DEPRECATED"
    assert body["request_id"]
    assert response.headers["Deprecation"] == "true"
    assert "Sunset" in response.headers
    assert "/api/v1/chatbot" in response.headers["Link"]


def test_legacy_portfolio_chat_route_is_not_routed_to_the_old_service(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-for-task18-login-tests")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")

    legacy_db_path = tmp_path / "legacy-chat-service.sqlite3"
    engine = create_engine(f"sqlite+pysqlite:///{legacy_db_path.as_posix()}")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_factory()
    auth_service = AuthService()
    _create_user(session, auth_service)

    app = _build_test_app(session, auth_service)
    client = TestClient(app)

    def _fail_if_called() -> object:
        raise AssertionError("legacy portfolio chat service should not be called")

    from app.services.portfolio_chat import get_portfolio_chat_service

    app.dependency_overrides[get_portfolio_chat_service] = _fail_if_called

    try:
        access_token = _login(client, "admin@example.com", "Secret123!")
        response = client.post(
            "/api/v1/chat/chat",
            json={"message": "What is this project?"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 410
