from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


@app.get("/api/v1/test/request-id-crash")
def _request_id_crash() -> None:
    raise RuntimeError("boom")


def _configure_test_env(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "request-id.sqlite3"
    database_url = f"sqlite+pysqlite:///{db_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("TEST_DATABASE_URL", database_url)
    monkeypatch.setenv("REDIS_URL", "")


def test_health_check_reuses_client_request_id_in_header_and_body(monkeypatch, tmp_path) -> None:
    _configure_test_env(monkeypatch, tmp_path)
    client = TestClient(app)
    request_id = "123e4567-e89b-12d3-a456-426614174000"

    response = client.get("/api/v1/health", headers={"X-Request-ID": request_id})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == request_id
    body = response.json()
    assert body["request_id"] == request_id
    assert body["success"] is True
    assert body["data"]["status"] == "ok"


def test_health_check_generates_request_id_when_missing(monkeypatch, tmp_path) -> None:
    _configure_test_env(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.headers["X-Request-ID"]
    body = response.json()
    assert body["request_id"] == response.headers["X-Request-ID"]
    assert body["request_id"]
    assert body["success"] is True
