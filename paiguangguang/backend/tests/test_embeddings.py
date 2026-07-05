from __future__ import annotations

from dataclasses import replace
import json

import httpx
import pytest

from app.ai.embeddings import (
    DashScopeEmbeddingProvider,
    EmbeddingConfigurationError,
    EmbeddingProviderError,
    HashEmbeddingProvider,
    get_embedding_provider,
)
from app.core.config import Settings
from app.storage.chroma_store import ChromaRagStore
import chromadb


def test_hash_embedding_provider_is_deterministic() -> None:
    provider = HashEmbeddingProvider()

    first = provider.embed(["Alpha beta", "Gamma delta"])
    second = provider.embed(["Alpha beta", "Gamma delta"])

    assert first == second
    assert len(first) == 2
    assert len(first[0]) == provider.dimension


def test_get_embedding_provider_uses_hash_by_default() -> None:
    provider = get_embedding_provider(Settings())

    assert isinstance(provider, HashEmbeddingProvider)


def test_dashscope_embedding_provider_requires_api_key() -> None:
    settings = replace(Settings(), embedding_provider="dashscope", dashscope_api_key="")

    with pytest.raises(EmbeddingConfigurationError, match="DASHSCOPE_API_KEY is required"):
        get_embedding_provider(settings)


def test_dashscope_embedding_provider_posts_openai_compatible_request() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.method == "POST"
        assert request.url.path == "/compatible-mode/v1/embeddings"
        assert request.headers["authorization"] == "Bearer test-key"
        assert request.headers["content-type"] == "application/json"
        payload = json.loads(request.content.decode("utf-8"))
        assert payload["model"] == "text-embedding-v1"
        assert payload["input"] == ["Alpha", "Beta"]
        assert payload["encoding_format"] == "float"
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": 0, "embedding": [0.1, 0.2, 0.3]},
                    {"index": 1, "embedding": [0.4, 0.5, 0.6]},
                ]
            },
        )

    provider = DashScopeEmbeddingProvider(
        settings=Settings(
            embedding_provider="dashscope",
            dashscope_api_key="test-key",
            dashscope_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            embedding_model="text-embedding-v1",
            embedding_timeout_seconds=5.0,
        ),
        transport=httpx.MockTransport(handler),
    )

    embeddings = provider.embed(["Alpha", "Beta"])

    assert len(requests) == 1
    assert embeddings == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]


def test_dashscope_embedding_provider_raises_on_invalid_response() -> None:
    provider = DashScopeEmbeddingProvider(
        settings=Settings(
            embedding_provider="dashscope",
            dashscope_api_key="test-key",
            dashscope_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            embedding_model="text-embedding-v1",
            embedding_timeout_seconds=5.0,
        ),
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"data": []})),
    )

    with pytest.raises(EmbeddingProviderError, match="did not include every embedding"):
        provider.embed(["Alpha"])


def test_chroma_store_uses_configured_embedding_provider(monkeypatch) -> None:
    monkeypatch.setenv("EMBEDDING_PROVIDER", "dashscope")
    monkeypatch.setenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

    with pytest.raises(EmbeddingConfigurationError, match="DASHSCOPE_API_KEY is required"):
        ChromaRagStore(client=chromadb.EphemeralClient())
