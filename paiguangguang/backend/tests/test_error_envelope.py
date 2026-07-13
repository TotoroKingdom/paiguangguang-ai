from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def _configure_test_env(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "error-envelope.sqlite3"
    database_url = f"sqlite+pysqlite:///{db_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("TEST_DATABASE_URL", database_url)
    monkeypatch.setenv("REDIS_URL", "")


def test_validation_error_uses_request_id_and_details(monkeypatch, tmp_path) -> None:
    _configure_test_env(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.post("/api/v1/auth/login", json={})

    assert response.status_code == 422
    assert response.headers["X-Request-ID"]
    body = response.json()
    assert body["request_id"] == response.headers["X-Request-ID"]
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["details"]


def test_unauthorized_error_uses_request_id(monkeypatch, tmp_path) -> None:
    _configure_test_env(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.headers["X-Request-ID"]
    body = response.json()
    assert body["request_id"] == response.headers["X-Request-ID"]
    assert body["success"] is False
    assert body["error"]["code"] == "AUTHENTICATION_ERROR"


def test_internal_error_is_wrapped_in_json_envelope() -> None:
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/api/v1/test/request-id-crash")

    assert response.status_code == 500
    assert response.headers["X-Request-ID"]
    body = response.json()
    assert body["request_id"] == response.headers["X-Request-ID"]
    assert body["success"] is False
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert body["error"]["message"] == "Internal server error"
