from __future__ import annotations

from collections.abc import Generator
import base64
import json
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from app.main import app as fastapi_app
from app.db.base import Base
from app.db.models import User
from app.db.session import get_db_session
from app.core.config import get_settings
from app.services.auth import AuthService, get_auth_service
from app.services.login_encryption import LoginEncryptionService, get_login_encryption_service
from app.storage.cache import InMemoryCacheAdapter


def _build_test_app(
    session: Session,
    auth_service: AuthService,
    login_encryption_service: LoginEncryptionService,
) -> FastAPI:
    app = fastapi_app
    app.dependency_overrides.clear()

    def override_db_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_login_encryption_service] = lambda: login_encryption_service
    return app


def _build_login_encryption(tmp_path, suffix: str):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    key_path = tmp_path / f"login-key-{suffix}.pem"
    key_path.write_bytes(
        private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    settings = get_settings()
    settings = settings.__class__(
        **{
            **settings.__dict__,
            "auth_login_private_key_path": str(key_path),
            "redis_url": "",
        }
    )
    return private_key, LoginEncryptionService(
        settings=settings,
        cache=InMemoryCacheAdapter(),
    )


def _encrypted_login_body(private_key, service, *, password: str, nonce: str):
    plaintext = json.dumps(
        {
            "password": password,
            "issued_at": int(datetime.now(timezone.utc).timestamp()),
            "nonce": nonce,
        },
        separators=(",", ":"),
    ).encode()
    ciphertext = private_key.public_key().encrypt(
        plaintext,
        padding.OAEP(
            mgf=padding.MGF1(hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return {
        "email": "admin@example.com",
        "encrypted_password": base64.urlsafe_b64encode(ciphertext).rstrip(b"=").decode(),
        "key_id": service.get_public_key_data().key_id,
    }


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
    private_key, encryption_service = _build_login_encryption(tmp_path, "valid")

    app = _build_test_app(session, auth_service, encryption_service)
    client = TestClient(app)

    key_response = client.get("/api/v1/auth/encryption-key")
    assert key_response.status_code == 200
    assert key_response.json()["data"]["key_id"] == encryption_service.get_public_key_data().key_id

    login_response = client.post(
        "/api/v1/auth/login",
        json=_encrypted_login_body(
            private_key,
            encryption_service,
            password="Secret123!",
            nonce="valid-login-nonce-0001",
        ),
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
    assert missing_token_response.json()["error"]["code"] == "AUTHENTICATION_ERROR"

    invalid_token_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert invalid_token_response.status_code == 401
    assert invalid_token_response.json()["error"]["code"] == "AUTHENTICATION_ERROR"

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
    private_key, encryption_service = _build_login_encryption(tmp_path, "invalid")

    app = _build_test_app(session, auth_service, encryption_service)
    client = TestClient(app)

    response = client.post(
        "/api/v1/auth/login",
        json=_encrypted_login_body(
            private_key,
            encryption_service,
            password="WrongPassword!",
            nonce="invalid-login-nonce-01",
        ),
    )

    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["error"]["message"] == "Invalid email or password"

    plaintext_response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "Secret123!"},
        headers={"X-Test-Plaintext-Login": "1"},
    )
    assert plaintext_response.status_code == 422

    app.dependency_overrides.clear()
    session.close()


def test_auth_login_populates_cached_user_context(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-for-task18-login-tests")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")

    engine = create_engine(f"sqlite+pysqlite:///{(tmp_path / 'auth-cache.sqlite3').as_posix()}")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_factory()
    auth_service = AuthService()
    _create_user(session, auth_service)
    private_key, encryption_service = _build_login_encryption(tmp_path, "cache")
    cache = InMemoryCacheAdapter()
    monkeypatch.setattr("app.services.auth.get_cache_adapter", lambda settings=None: cache, raising=False)

    app = _build_test_app(session, auth_service, encryption_service)
    client = TestClient(app)

    login_response = client.post(
        "/api/v1/auth/login",
        json=_encrypted_login_body(
            private_key,
            encryption_service,
            password="Secret123!",
            nonce="cache-login-nonce-0001",
        ),
    )

    assert login_response.status_code == 200
    cached_entries = [cache.get(key) for key in cache._values]
    assert any(
        entry is not None
        and entry["email"] == "admin@example.com"
        and "effective_permissions" in entry
        and "workspace_ids" in entry
        for entry in cached_entries
    )

    app.dependency_overrides.clear()
    session.close()


def test_auth_me_uses_cached_user_context(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-for-task18-login-tests")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")

    engine = create_engine(f"sqlite+pysqlite:///{(tmp_path / 'auth-me-cache.sqlite3').as_posix()}")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_factory()
    auth_service = AuthService()
    _create_user(session, auth_service)
    private_key, encryption_service = _build_login_encryption(tmp_path, "me-cache")
    cache = InMemoryCacheAdapter()
    monkeypatch.setattr("app.services.auth.get_cache_adapter", lambda settings=None: cache, raising=False)

    app = _build_test_app(session, auth_service, encryption_service)
    client = TestClient(app)

    login_response = client.post(
        "/api/v1/auth/login",
        json=_encrypted_login_body(
            private_key,
            encryption_service,
            password="Secret123!",
            nonce="me-cache-login-nonce",
        ),
    )
    access_token = login_response.json()["data"]["access_token"]
    auth_service.get_user_by_id = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("database lookup should be skipped"))  # type: ignore[method-assign]

    me_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert me_response.status_code == 200
    assert me_response.json()["data"]["email"] == "admin@example.com"

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
