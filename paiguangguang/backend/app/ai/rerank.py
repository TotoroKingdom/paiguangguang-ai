from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Protocol, Sequence

import httpx

from app.core.config import Settings, get_settings


class RerankProvider(Protocol):
    def rerank(self, query: str, documents: Sequence[str], *, top_n: int | None = None) -> list["RerankResult"]:
        ...


@dataclass(frozen=True)
class RerankResult:
    index: int
    relevance_score: float


class RerankProviderError(RuntimeError):
    pass


class RerankProviderTimeoutError(RerankProviderError):
    pass


class RerankConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class DeterministicRerankProvider:
    def rerank(self, query: str, documents: Sequence[str], *, top_n: int | None = None) -> list[RerankResult]:
        scored = [
            RerankResult(index=index, relevance_score=_deterministic_score(query, document, index))
            for index, document in enumerate(documents)
        ]
        scored.sort(key=lambda item: (-item.relevance_score, item.index))
        if top_n is not None:
            return scored[:top_n]
        return scored


class DashScopeRerankProvider:
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
        self.model = model or self.settings.rerank_model
        self.timeout_seconds = timeout_seconds or self.settings.rerank_timeout_seconds
        if not self.api_key:
            raise RerankConfigurationError(
                "DASHSCOPE_API_KEY is required when RERANK_PROVIDER=dashscope"
            )
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout_seconds,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "DashScopeRerankProvider":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def rerank(self, query: str, documents: Sequence[str], *, top_n: int | None = None) -> list[RerankResult]:
        if not documents:
            return []

        payload: dict[str, Any] = {
            "model": self.model,
            "query": query,
            "documents": list(documents),
        }
        if top_n is not None:
            payload["top_n"] = top_n

        try:
            response = self._client.post(
                "/reranks",
                headers=self._auth_headers(),
                json=payload,
            )
        except httpx.TimeoutException as exc:
            raise RerankProviderTimeoutError(
                f"DashScope rerank request timed out after {self.timeout_seconds:.1f} seconds"
            ) from exc
        except httpx.RequestError as exc:
            raise RerankProviderError(f"DashScope rerank request failed: {exc}") from exc

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text.strip()
            raise RerankProviderError(
                f"DashScope rerank request failed with HTTP {exc.response.status_code}: {detail}"
            ) from exc

        data = response.json()
        if not isinstance(data, dict):
            raise RerankProviderError("DashScope returned an invalid JSON payload")

        results = self._extract_results(data)
        rerank_results: list[RerankResult] = []
        for item in results:
            if not isinstance(item, dict):
                continue
            index = item.get("index")
            score = item.get("relevance_score")
            if isinstance(index, int) and isinstance(score, (int, float)):
                rerank_results.append(RerankResult(index=index, relevance_score=float(score)))

        if not rerank_results:
            raise RerankProviderError("DashScope response did not include any rerank results")

        rerank_results.sort(key=lambda item: (-item.relevance_score, item.index))
        if top_n is not None:
            return rerank_results[:top_n]
        return rerank_results

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _extract_results(payload: dict[str, Any]) -> list[dict[str, Any]]:
        results = payload.get("results")
        if isinstance(results, list):
            return results
        output = payload.get("output")
        if isinstance(output, dict):
            nested = output.get("results")
            if isinstance(nested, list):
                return nested
        raise RerankProviderError("DashScope returned an invalid rerank payload")


def _deterministic_score(query: str, document: str, index: int) -> float:
    query_terms = _tokenize(query)
    document_terms = _tokenize(document)
    if not query_terms or not document_terms:
        return 0.0

    overlap = len(query_terms & document_terms)
    exact = 1.0 if query.lower().strip() in document.lower() else 0.0
    prefix = 1.0 if document.lower().startswith(query.lower().strip()) else 0.0
    length_bonus = min(len(document_terms) / max(len(query_terms), 1), 3.0) * 0.05
    return exact * 5.0 + prefix * 1.5 + overlap * 1.25 + length_bonus + (1.0 / (index + 1)) * 0.01


def _tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9_./:-]+", text.lower()) if token}


def get_rerank_provider(settings: Settings | None = None) -> RerankProvider | None:
    resolved_settings = settings or get_settings()
    provider_name = resolved_settings.rerank_provider.strip().lower()
    if provider_name in {"", "none", "off", "disabled"}:
        return None
    if provider_name in {"fake", "deterministic"}:
        return DeterministicRerankProvider()
    if provider_name in {"dashscope", "aliyun", "alibaba"}:
        return DashScopeRerankProvider(settings=resolved_settings)
    raise RerankConfigurationError(f"Unknown rerank provider: {resolved_settings.rerank_provider}")
