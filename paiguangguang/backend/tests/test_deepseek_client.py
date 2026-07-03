from __future__ import annotations

import json

import httpx
import pytest

from app.ai.deepseek import DeepSeekClient, DeepSeekError


def test_deepseek_client_requires_api_key() -> None:
    client = DeepSeekClient(api_key="")

    with pytest.raises(ValueError, match="DEEPSEEK_API_KEY is required"):
        client.chat_completions([{"role": "user", "content": "Hello"}])


def test_deepseek_client_sends_chat_completion_request() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-123",
                "object": "chat.completion",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "Hello back"},
                        "finish_reason": "stop",
                    }
                ],
            },
        )

    transport = httpx.MockTransport(handler)
    client = DeepSeekClient(
        api_key="test-key",
        base_url="https://api.deepseek.com",
        transport=transport,
    )

    result = client.chat_completions(
        [{"role": "user", "content": "Hello"}],
        temperature=0.2,
    )

    assert captured["method"] == "POST"
    assert captured["url"] == "https://api.deepseek.com/v1/chat/completions"
    assert captured["body"] == {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": False,
        "temperature": 0.2,
    }
    assert result["choices"][0]["message"]["content"] == "Hello back"


def test_deepseek_client_raises_clear_error_for_http_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "invalid key"}})

    transport = httpx.MockTransport(handler)
    client = DeepSeekClient(api_key="bad-key", transport=transport)

    with pytest.raises(DeepSeekError, match="HTTP 401"):
        client.chat_completions([{"role": "user", "content": "Hello"}])
