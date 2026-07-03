from __future__ import annotations

from typing import Any, Sequence

import httpx

from app.core.config import Settings, get_settings


class DeepSeekError(RuntimeError):
    pass


class DeepSeekClient:
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
        self.api_key = api_key if api_key is not None else self.settings.deepseek_api_key
        self.base_url = (base_url or self.settings.deepseek_base_url).rstrip("/")
        self.model = model or self.settings.deepseek_chat_model
        self.timeout_seconds = timeout_seconds or self.settings.deepseek_timeout_seconds
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout_seconds,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "DeepSeekClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _auth_headers(self) -> dict[str, str]:
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY is required")
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def chat_completions(
        self,
        messages: Sequence[dict[str, Any]],
        *,
        model: str | None = None,
        temperature: float | None = None,
        stream: bool = False,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model or self.model,
            "messages": list(messages),
            "stream": stream,
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if extra:
            payload.update(extra)

        response = self._client.post(
            "/v1/chat/completions",
            headers=self._auth_headers(),
            json=payload,
        )

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text.strip()
            raise DeepSeekError(
                f"DeepSeek request failed with HTTP {exc.response.status_code}: {detail}"
            ) from exc

        data = response.json()
        if not isinstance(data, dict):
            raise DeepSeekError("DeepSeek returned an invalid JSON payload")
        return data
