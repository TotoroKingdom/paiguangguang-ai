from __future__ import annotations

import json
from dataclasses import dataclass

import httpx
import pytest

from app.chatbot.llm.deepseek_provider import DeepSeekProvider
from app.chatbot.llm.exceptions import LLMProviderError, LLMProtocolError, LLMRateLimitError, LLMTimeoutError
from app.chatbot.llm.provider import ChatCompletionRequest, LLMMessage


@dataclass
class _ChunkedStream(httpx.SyncByteStream):
    chunks: list[bytes]
    error: Exception | None = None

    def __iter__(self):
        for chunk in self.chunks:
            yield chunk
        if self.error is not None:
            raise self.error

    def close(self) -> None:
        return None


def _build_request() -> ChatCompletionRequest:
    return ChatCompletionRequest(
        request_id="req-1",
        prompt_version="chatbot-v1",
        model="deepseek-chat",
        messages=(LLMMessage(role="user", content="Hello"),),
        temperature=0.2,
    )


def test_deepseek_provider_complete_posts_expected_payload_and_parses_result() -> None:
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
                "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
            },
        )

    provider = DeepSeekProvider(
        api_key="test-key",
        base_url="https://api.deepseek.com",
        transport=httpx.MockTransport(handler),
    )

    result = provider.complete(_build_request())

    assert captured["method"] == "POST"
    assert captured["url"] == "https://api.deepseek.com/v1/chat/completions"
    assert captured["body"] == {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": False,
        "temperature": 0.2,
    }
    assert result.message.role == "assistant"
    assert result.message.content == "Hello back"
    assert result.finish_reason == "stop"
    assert result.usage is not None
    assert result.usage.total_tokens == 7


def test_deepseek_provider_stream_parses_chunked_sse_and_usage() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        stream = _ChunkedStream(
            chunks=[
                b"data: {\"choices\":[{\"delta\":{\"role\":\"assistant\"}}]}\n",
                b"\n",
                b"data: {\"choices\":[{\"delta\":{\"content\":\"Hello\"}}]}\n\n",
                b"data: {\"choices\":[{\"delta\":{\"content\":\" world\"},\"finish_reason\":\"stop\"}],",
                b"\"usage\":{\"prompt_tokens\":10,\"completion_tokens\":2,\"total_tokens\":12}}\n\n",
                b"data: [DONE]\n\n",
            ]
        )
        return httpx.Response(200, stream=stream)

    provider = DeepSeekProvider(
        api_key="test-key",
        base_url="https://api.deepseek.com",
        transport=httpx.MockTransport(handler),
    )

    events = list(provider.stream(_build_request()))

    assert [event.kind for event in events] == ["delta", "delta", "usage", "completed"]
    assert [event.content for event in events if event.kind == "delta"] == ["Hello", " world"]
    completed = events[-1]
    assert completed.finish_reason == "stop"
    assert completed.content == "Hello world"
    assert completed.usage is not None
    assert completed.usage.prompt_tokens == 10


def test_deepseek_provider_raises_rate_limit_for_429() -> None:
    provider = DeepSeekProvider(
        api_key="test-key",
        transport=httpx.MockTransport(lambda _request: httpx.Response(429, json={"error": {"message": "slow down"}})),
    )

    with pytest.raises(LLMRateLimitError):
        provider.complete(_build_request())


def test_deepseek_provider_raises_provider_error_for_5xx() -> None:
    provider = DeepSeekProvider(
        api_key="test-key",
        transport=httpx.MockTransport(lambda _request: httpx.Response(502, text="bad gateway")),
    )

    with pytest.raises(LLMProviderError, match="HTTP 502"):
        provider.complete(_build_request())


def test_deepseek_provider_raises_protocol_error_for_invalid_json() -> None:
    provider = DeepSeekProvider(
        api_key="test-key",
        transport=httpx.MockTransport(lambda _request: httpx.Response(200, text="not json")),
    )

    with pytest.raises(LLMProtocolError):
        provider.complete(_build_request())


def test_deepseek_provider_maps_timeout_exception() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout")

    provider = DeepSeekProvider(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(LLMTimeoutError):
        provider.complete(_build_request())


def test_deepseek_provider_allows_missing_usage() -> None:
    provider = DeepSeekProvider(
        api_key="test-key",
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": "Hello back"},
                            "finish_reason": "stop",
                        }
                    ],
                },
            )
        ),
    )

    result = provider.complete(_build_request())

    assert result.finish_reason == "stop"
    assert result.usage is None


def test_deepseek_provider_raises_for_truncated_stream() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        stream = _ChunkedStream(
            chunks=[b"data: {\"choices\":[{\"delta\":{\"content\":\"Hello\"}}]}\n\n"],
            error=httpx.ReadError("connection dropped"),
        )
        return httpx.Response(200, stream=stream)

    provider = DeepSeekProvider(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )

    iterator = provider.stream(_build_request())
    first_event = next(iterator)
    assert first_event.kind == "delta"

    with pytest.raises(LLMProviderError, match="connection dropped"):
        list(iterator)


def test_deepseek_provider_close_is_idempotent() -> None:
    provider = DeepSeekProvider(api_key="test-key")
    provider.close()
    provider.close()
