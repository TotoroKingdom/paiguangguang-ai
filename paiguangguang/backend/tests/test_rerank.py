from __future__ import annotations

import json

import httpx
import pytest

from app.ai.rerank import (
    DashScopeRerankProvider,
    DeterministicRerankProvider,
    RerankConfigurationError,
    RerankProviderError,
    get_rerank_provider,
)
from app.core.config import Settings


def test_deterministic_rerank_provider_is_stable() -> None:
    provider = DeterministicRerankProvider()

    first = provider.rerank(
        "How is deployment organized?",
        ["Alpha deployment notes.", "Beta deployment notes."],
    )
    second = provider.rerank(
        "How is deployment organized?",
        ["Alpha deployment notes.", "Beta deployment notes."],
    )

    assert first == second
    assert len(first) == 2
    assert first[0].relevance_score >= first[1].relevance_score


def test_get_rerank_provider_uses_none_by_default() -> None:
    assert get_rerank_provider(Settings()) is None


def test_dashscope_rerank_provider_requires_api_key() -> None:
    settings = Settings(rerank_provider="dashscope", dashscope_api_key="")

    with pytest.raises(RerankConfigurationError, match="DASHSCOPE_API_KEY is required"):
        DashScopeRerankProvider(settings=settings)


def test_dashscope_rerank_provider_posts_openai_compatible_request() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.method == "POST"
        assert request.url.path == "/compatible-mode/v1/reranks"
        assert request.headers["authorization"] == "Bearer test-key"
        assert request.headers["content-type"] == "application/json"
        payload = json.loads(request.content.decode("utf-8"))
        assert payload["model"] == "qwen3-rerank"
        assert payload["query"] == "How is deployment organized?"
        assert payload["documents"] == ["Alpha notes", "Beta notes"]
        assert payload["top_n"] == 2
        return httpx.Response(
            200,
            json={
                "results": [
                    {"index": 1, "relevance_score": 0.93},
                    {"index": 0, "relevance_score": 0.51},
                ]
            },
        )

    provider = DashScopeRerankProvider(
        settings=Settings(
            rerank_provider="dashscope",
            dashscope_api_key="test-key",
            dashscope_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            rerank_model="qwen3-rerank",
            rerank_timeout_seconds=5.0,
        ),
        transport=httpx.MockTransport(handler),
    )

    results = provider.rerank("How is deployment organized?", ["Alpha notes", "Beta notes"], top_n=2)

    assert len(requests) == 1
    assert [result.index for result in results] == [1, 0]
    assert [result.relevance_score for result in results] == [0.93, 0.51]


def test_dashscope_rerank_provider_raises_on_invalid_response() -> None:
    provider = DashScopeRerankProvider(
        settings=Settings(
            rerank_provider="dashscope",
            dashscope_api_key="test-key",
            dashscope_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            rerank_model="qwen3-rerank",
            rerank_timeout_seconds=5.0,
        ),
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"results": [{}]})),
    )

    with pytest.raises(RerankProviderError, match="did not include any rerank results"):
        provider.rerank("How is deployment organized?", ["Alpha notes"], top_n=1)
