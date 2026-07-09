from __future__ import annotations

import json

import httpx
from fastapi.testclient import TestClient

from app.ai.deepseek import DeepSeekClient
from app.main import app
from app.services.portfolio_chat import PortfolioChatMemory, PortfolioChatService, get_portfolio_chat_service


def _build_chat_service(handler):
    transport = httpx.MockTransport(handler)
    client = DeepSeekClient(api_key="test-key", transport=transport)
    memory = PortfolioChatMemory()
    return PortfolioChatService(client=client, memory=memory)


def test_portfolio_chat_returns_reply_and_session_id() -> None:
    captured_bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_bodies.append(json.loads(request.content.decode()))
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "I can help with the portfolio and project walkthrough.",
                        }
                    }
                ]
            },
        )

    service = _build_chat_service(handler)
    app.dependency_overrides[get_portfolio_chat_service] = lambda: service
    client = TestClient(app)

    try:
        response = client.post("/api/v1/chat/chat", json={"message": "What is this project?"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["reply"] == "I can help with the portfolio and project walkthrough."
    assert isinstance(body["data"]["session_id"], str)
    assert len(captured_bodies) == 1
    assert captured_bodies[0]["messages"][0]["role"] == "system"
    assert captured_bodies[0]["messages"][-1] == {"role": "user", "content": "What is this project?"}


def test_portfolio_chat_uses_session_memory() -> None:
    captured_bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_bodies.append(json.loads(request.content.decode()))
        reply = "First answer" if len(captured_bodies) == 1 else "Second answer"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": reply,
                        }
                    }
                ]
            },
        )

    service = _build_chat_service(handler)
    app.dependency_overrides[get_portfolio_chat_service] = lambda: service
    client = TestClient(app)

    try:
        first_response = client.post("/api/v1/chat/chat", json={"message": "Hi"})
        session_id = first_response.json()["data"]["session_id"]
        second_response = client.post(
            "/api/v1/chat/chat",
            json={"message": "What did I ask before?", "session_id": session_id},
        )
    finally:
        app.dependency_overrides.clear()

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert captured_bodies[1]["messages"][-3:] == [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "First answer"},
        {"role": "user", "content": "What did I ask before?"},
    ]


def test_portfolio_chat_validation_error_is_enveloped() -> None:
    client = TestClient(app)

    response = client.post("/api/v1/chat/chat", json={"message": ""})

    assert response.status_code == 422
    assert response.json()["success"] is False
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_portfolio_chat_legacy_endpoint_is_not_available() -> None:
    client = TestClient(app)

    response = client.post("/api/v1/chat/portfolio", json={"message": "What is this project?"})

    assert response.status_code == 404
