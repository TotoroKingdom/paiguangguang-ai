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
        email="owner@example.com",
        display_name="Owner",
        password="Secret123!",
        is_active=True,
    )


def test_legacy_chat_compatibility_returns_deprecation_headers_without_legacy_service(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-for-task18-login-tests")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")

    legacy_db_path = tmp_path / "legacy-chat-compat.sqlite3"
    engine = create_engine(f"sqlite+pysqlite:///{legacy_db_path.as_posix()}")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_factory()
    auth_service = AuthService()
    _create_user(session, auth_service)

    app = _build_test_app(session, auth_service)
    client = TestClient(app)

    from app.services.portfolio_chat import get_portfolio_chat_service

    app.dependency_overrides[get_portfolio_chat_service] = lambda: (_ for _ in ()).throw(
        AssertionError("legacy portfolio chat service should not be invoked")
    )

    try:
        login_response = client.post("/api/v1/auth/login", json={"email": "owner@example.com", "password": "Secret123!"})
        access_token = login_response.json()["data"]["access_token"]
        response = client.post(
            "/api/v1/chat/chat",
            json={"message": "What is this project?"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 410
    assert response.json()["error"]["code"] == "CHATBOT_LEGACY_CHAT_DEPRECATED"
