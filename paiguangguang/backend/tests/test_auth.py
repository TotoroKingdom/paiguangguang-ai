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
from app.core.config import get_settings
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


def test_auth_login_me_and_invalid_token(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-for-task18-login-tests")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")

    engine = create_engine(f"sqlite+pysqlite:///{(tmp_path / 'auth.sqlite3').as_posix()}")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_factory()
    auth_service = AuthService()
    _create_user(session, auth_service)

    app = _build_test_app(session, auth_service)
    client = TestClient(app)

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "Secret123!"},
    )
    assert login_response.status_code == 200
    login_body = login_response.json()
    assert login_body["success"] is True
    assert login_body["data"]["access_token"]
    assert login_body["data"]["token_type"] == "bearer"

    access_token = login_body["data"]["access_token"]
    me_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_response.status_code == 200
    me_body = me_response.json()
    assert me_body["success"] is True
    assert me_body["data"]["email"] == "admin@example.com"
    assert me_body["data"]["display_name"] == "Admin User"
    assert me_body["data"]["is_active"] is True

    missing_token_response = client.get("/api/v1/auth/me")
    assert missing_token_response.status_code == 401
    assert missing_token_response.json()["error"]["code"] == "HTTP_ERROR"

    invalid_token_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert invalid_token_response.status_code == 401
    assert invalid_token_response.json()["error"]["code"] == "HTTP_ERROR"

    app.dependency_overrides.clear()
    session.close()


def test_auth_login_rejects_invalid_password(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-for-task18-login-tests")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")

    engine = create_engine(f"sqlite+pysqlite:///{(tmp_path / 'auth-invalid.sqlite3').as_posix()}")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_factory()
    auth_service = AuthService()
    _create_user(session, auth_service)

    app = _build_test_app(session, auth_service)
    client = TestClient(app)

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "WrongPassword!"},
    )

    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["error"]["message"] == "Invalid email or password"

    app.dependency_overrides.clear()
    session.close()


def test_auth_settings_load_jwt_configuration(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-for-task18-login-tests")
    monkeypatch.setenv("JWT_ALGORITHM", "HS384")
    monkeypatch.setenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "45")

    settings = get_settings()

    assert settings.jwt_secret_key == "test-secret-key-for-task18-login-tests"
    assert settings.jwt_algorithm == "HS384"
    assert settings.jwt_access_token_expire_minutes == 45
