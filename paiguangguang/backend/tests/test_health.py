from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_standard_response_envelope() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ok"
    assert body["data"]["cache_backend"] in {"memory", "redis"}
    assert isinstance(body["data"]["knowledge_base_version"], str)
    assert body["error"] is None
