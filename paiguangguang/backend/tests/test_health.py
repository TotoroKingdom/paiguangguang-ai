from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_removed_business_api_is_not_found() -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 404
