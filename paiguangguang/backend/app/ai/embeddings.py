from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from typing import Any, Protocol, Sequence

import httpx

from app.core.config import Settings, get_settings
from app.storage.cache import CacheAdapter
from app.services.rag_cache import build_shared_cache_key


class EmbeddingProvider(Protocol):
    dimension: int

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        ...


class EmbeddingProviderError(RuntimeError):
    pass


class EmbeddingProviderTimeoutError(EmbeddingProviderError):
    pass


class EmbeddingConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class HashEmbeddingProvider:
    dimension: int = 64

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        if not tokens:
            return [0.0] * self.dimension

        vector = [0.0] * self.dimension
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            weight = 1.0 + (digest[5] / 255.0) * 0.25
            vector[index] += sign * weight

        norm = math.sqrt(sum(value * value for value in vector))
        if not norm:
            return vector
        return [value / norm for value in vector]


@dataclass
class CachingEmbeddingProvider:
    provider: EmbeddingProvider
    cache_adapter: CacheAdapter
    model_version: str
    namespace: str = "embedding"
    cache_bypass: bool = False

    @property
    def dimension(self) -> int:
        return getattr(self.provider, "dimension", 0)

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []

        if self.cache_bypass:
            return self.provider.embed(texts)

        cache_key = build_shared_cache_key(
            self.namespace,
            model_version=self.model_version,
            payload={"texts": list(texts), "dimension": self.dimension},
        )
        cached = self.cache_adapter.get(cache_key)
        if isinstance(cached, list):
            return [[float(value) for value in embedding] for embedding in cached if isinstance(embedding, list)]

        embeddings = self.provider.embed(texts)
        self.cache_adapter.set(cache_key, embeddings)
        return embeddings


class DashScopeEmbeddingProvider:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.api_key = api_key if api_key is not None else self.settings.dashscope_api_key
        self.base_url = (base_url or self.settings.dashscope_base_url).rstrip("/")
        self.model = model or self.settings.embedding_model
        self.timeout_seconds = timeout_seconds or self.settings.embedding_timeout_seconds
        if not self.api_key:
            raise EmbeddingConfigurationError(
                "DASHSCOPE_API_KEY is required when EMBEDDING_PROVIDER=dashscope"
            )
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout_seconds,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "DashScopeEmbeddingProvider":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    @property
    def dimension(self) -> int:
        return 0

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []

        try:
            response = self._client.post(
                "/embeddings",
                headers=self._auth_headers(),
                json={
                    "model": self.model,
                    "input": list(texts),
                    "encoding_format": "float",
                },
            )
        except httpx.TimeoutException as exc:
            raise EmbeddingProviderTimeoutError(
                f"DashScope embedding request timed out after {self.timeout_seconds:.1f} seconds"
            ) from exc
        except httpx.RequestError as exc:
            raise EmbeddingProviderError(f"DashScope embedding request failed: {exc}") from exc

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text.strip()
            raise EmbeddingProviderError(
                f"DashScope embedding request failed with HTTP {exc.response.status_code}: {detail}"
            ) from exc

        data = response.json()
        if not isinstance(data, dict):
            raise EmbeddingProviderError("DashScope returned an invalid JSON payload")

        payload = data.get("data")
        if not isinstance(payload, list):
            raise EmbeddingProviderError("DashScope returned an invalid embedding payload")

        indexed_embeddings: dict[int, list[float]] = {}
        for item in payload:
            if not isinstance(item, dict):
                continue
            index = item.get("index")
            embedding = item.get("embedding")
            if isinstance(index, int) and isinstance(embedding, list):
                indexed_embeddings[index] = [float(value) for value in embedding]

        embeddings: list[list[float]] = []
        for index in range(len(texts)):
            if index not in indexed_embeddings:
                raise EmbeddingProviderError("DashScope response did not include every embedding")
            embeddings.append(indexed_embeddings[index])
        return embeddings


def get_embedding_provider(settings: Settings | None = None) -> EmbeddingProvider:
    resolved_settings = settings or get_settings()
    provider_name = resolved_settings.embedding_provider.strip().lower()
    if provider_name in {"", "hash", "fake", "deterministic"}:
        return HashEmbeddingProvider()
    if provider_name in {"dashscope", "aliyun", "alibaba"}:
        return DashScopeEmbeddingProvider(settings=resolved_settings)
    raise EmbeddingConfigurationError(f"Unknown embedding provider: {resolved_settings.embedding_provider}")
