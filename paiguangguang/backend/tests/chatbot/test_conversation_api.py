from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.main import app as fastapi_app
from app.db.base import Base
from app.db.models import User
from app.db.session import get_db_session
from app.services.auth import AuthService, get_auth_service
from app.core.config import Settings, get_settings


def _build_session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_engine(f"sqlite+pysqlite:///{(tmp_path / f'{uuid4()}.sqlite3').as_posix()}", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def _build_test_app(session: Session, auth_service: AuthService) -> FastAPI:
    app = fastapi_app
    app.dependency_overrides.clear()

    def override_db_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    return app


def _create_user(session: Session, auth_service: AuthService, *, email: str) -> User:
    return auth_service.create_user(
        session,
        email=email,
        display_name=email.split("@")[0].title(),
        password="Secret123!",
        is_active=True,
    )


def test_conversation_api_returns_503_when_chatbot_is_disabled(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-for-chatbot-api")
    session_factory = _build_session_factory(tmp_path)
    session = session_factory()
    auth_service = AuthService()
    owner = _create_user(session, auth_service, email="disabled-owner@example.com")
    app = _build_test_app(session, auth_service)
    app.dependency_overrides[get_settings] = lambda: Settings(chatbot_enabled=False)
    client = TestClient(app)
    try:
        login = client.post(
            "/api/v1/auth/login",
            json={"email": owner.email, "password": "Secret123!"},
        )
        headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}
        response = client.get("/api/v1/chatbot/conversations", headers=headers)
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "CHATBOT_DISABLED"
    finally:
        app.dependency_overrides.clear()
        session.close()


def test_conversation_api_crud_owner_filter_and_router_registration(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-for-chatbot-api")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")

    session_factory = _build_session_factory(tmp_path)
    session = session_factory()
    auth_service = AuthService()
    owner = _create_user(session, auth_service, email="owner@example.com")
    foreign = _create_user(session, auth_service, email="foreign@example.com")

    app = _build_test_app(session, auth_service)
    client = TestClient(app)

    try:
        openapi_paths = app.openapi()["paths"]
        assert "/api/v1/chatbot/conversations" in openapi_paths

        owner_login = client.post("/api/v1/auth/login", json={"email": owner.email, "password": "Secret123!"})
        foreign_login = client.post("/api/v1/auth/login", json={"email": foreign.email, "password": "Secret123!"})
        owner_headers = {"Authorization": f"Bearer {owner_login.json()['data']['access_token']}"}
        foreign_headers = {"Authorization": f"Bearer {foreign_login.json()['data']['access_token']}"}

        first_create = client.post(
            "/api/v1/chatbot/conversations",
            headers=owner_headers,
            json={"title": "  新对话标题  "},
        )
        assert first_create.status_code == 201
        first_body = first_create.json()["data"]
        assert first_body["title"] == "新对话标题"
        assert first_body["title_source"] == "manual"
        assert first_body["model"] == "deepseek-chat"

        second_create = client.post("/api/v1/chatbot/conversations", headers=owner_headers, json={})
        assert second_create.status_code == 201
        second_body = second_create.json()["data"]
        assert second_body["title"] == "新对话"
        assert second_body["title_source"] == "default"

        list_response = client.get("/api/v1/chatbot/conversations?status=active&limit=1", headers=owner_headers)
        assert list_response.status_code == 200
        list_payload = list_response.json()["data"]
        assert len(list_payload["items"]) == 1
        assert list_payload["has_more"] is True

        next_page = client.get(
            f"/api/v1/chatbot/conversations?status=active&limit=1&cursor={list_payload['next_cursor']}",
            headers=owner_headers,
        )
        assert next_page.status_code == 200
        assert len(next_page.json()["data"]["items"]) == 1

        detail_response = client.get(f"/api/v1/chatbot/conversations/{second_body['id']}", headers=owner_headers)
        assert detail_response.status_code == 200
        assert detail_response.json()["data"]["id"] == second_body["id"]

        update_response = client.patch(
            f"/api/v1/chatbot/conversations/{second_body['id']}",
            headers=owner_headers,
            json={"title": "  更新后的标题  ", "model": "deepseek-chat"},
        )
        assert update_response.status_code == 200
        assert update_response.json()["data"]["title"] == "更新后的标题"
        assert update_response.json()["data"]["title_source"] == "manual"

        archive_response = client.post(f"/api/v1/chatbot/conversations/{second_body['id']}/archive", headers=owner_headers)
        assert archive_response.status_code == 200
        assert archive_response.json()["data"]["status"] == "archived"

        archive_again = client.post(f"/api/v1/chatbot/conversations/{second_body['id']}/archive", headers=owner_headers)
        assert archive_again.status_code == 200
        assert archive_again.json()["data"]["status"] == "archived"

        restore_response = client.post(f"/api/v1/chatbot/conversations/{second_body['id']}/restore", headers=owner_headers)
        assert restore_response.status_code == 200
        assert restore_response.json()["data"]["status"] == "active"

        delete_response = client.delete(f"/api/v1/chatbot/conversations/{second_body['id']}", headers=owner_headers)
        assert delete_response.status_code == 200
        assert delete_response.json()["data"]["status"] == "deleted"

        second_delete = client.delete(f"/api/v1/chatbot/conversations/{second_body['id']}", headers=owner_headers)
        assert second_delete.status_code == 404
        assert second_delete.json()["error"]["code"] == "CHATBOT_CONVERSATION_NOT_FOUND"

        foreign_detail = client.get(f"/api/v1/chatbot/conversations/{first_body['id']}", headers=foreign_headers)
        assert foreign_detail.status_code == 404
        assert foreign_detail.json()["error"]["code"] == "CHATBOT_CONVERSATION_NOT_FOUND"
    finally:
        app.dependency_overrides.clear()
        session.close()


def test_conversation_api_rejects_invalid_model_cursor_and_missing_auth(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-for-chatbot-api")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")

    session_factory = _build_session_factory(tmp_path)
    session = session_factory()
    auth_service = AuthService()
    user = _create_user(session, auth_service, email="owner@example.com")

    app = _build_test_app(session, auth_service)
    client = TestClient(app)

    try:
        no_auth_response = client.get("/api/v1/chatbot/conversations")
        assert no_auth_response.status_code == 401
        assert no_auth_response.json()["error"]["code"] == "AUTHENTICATION_ERROR"

        login_response = client.post("/api/v1/auth/login", json={"email": user.email, "password": "Secret123!"})
        headers = {"Authorization": f"Bearer {login_response.json()['data']['access_token']}"}

        invalid_model_response = client.post(
            "/api/v1/chatbot/conversations",
            headers=headers,
            json={"title": "hello", "model": "gpt-4"},
        )
        assert invalid_model_response.status_code == 422
        assert invalid_model_response.json()["error"]["code"] == "CHATBOT_MODEL_NOT_ALLOWED"

        valid_create = client.post("/api/v1/chatbot/conversations", headers=headers, json={"title": "first"})
        conversation_id = valid_create.json()["data"]["id"]

        invalid_cursor_response = client.get(
            "/api/v1/chatbot/conversations?status=active&cursor=not-a-cursor",
            headers=headers,
        )
        assert invalid_cursor_response.status_code == 400
        assert invalid_cursor_response.json()["error"]["code"] == "CHATBOT_INVALID_CURSOR"

        assert client.get(f"/api/v1/chatbot/conversations/{conversation_id}", headers=headers).status_code == 200
    finally:
        app.dependency_overrides.clear()
        session.close()
