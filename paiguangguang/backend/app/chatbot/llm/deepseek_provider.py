from __future__ import annotations

from typing import Any

import httpx

from app.chatbot.llm.exceptions import (
    LLMConfigurationError,
    LLMProviderError,
    LLMProtocolError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from app.chatbot.llm.provider import (
    ChatCompletionRequest,
    ChatCompletionResult,
    ChatCompletionUsage,
    LLMMessage,
    LLMStreamEvent,
)
from app.chatbot.llm.streaming import decode_sse_payload, iter_sse_payloads
from app.core.config import Settings, get_settings


class DeepSeekProvider:
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
        self.model = model or self.settings.chatbot_default_model
        self.timeout_seconds = (
            timeout_seconds if timeout_seconds is not None else self.settings.chatbot_llm_timeout_seconds
        )
        if not self.api_key:
            raise LLMConfigurationError("DEEPSEEK_API_KEY is required for the DeepSeek provider")
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout_seconds,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "DeepSeekProvider":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def complete(self, request: ChatCompletionRequest) -> ChatCompletionResult:
        response = self._request(request, stream=False)
        data = self._parse_json_response(response)
        return self._parse_completion_result(request, data)

    def stream(self, request: ChatCompletionRequest):
        try:
            with self._client.stream(
                "POST",
                "/v1/chat/completions",
                headers=self._auth_headers(),
                json=request.to_payload(stream=True),
            ) as response:
                self._raise_for_status(response)
                content_parts: list[str] = []
                finish_reason: str | None = None
                usage: ChatCompletionUsage | None = None
                for raw_payload in iter_sse_payloads(response):
                    decoded = decode_sse_payload(raw_payload)
                    if decoded == "[DONE]":
                        break
                    assert isinstance(decoded, dict)
                    choice = self._first_choice(decoded)
                    delta = choice.get("delta")
                    if isinstance(delta, dict):
                        content = delta.get("content")
                        if isinstance(content, str) and content:
                            content_parts.append(content)
                            yield LLMStreamEvent(
                                kind="delta",
                                request_id=request.request_id,
                                prompt_version=request.prompt_version,
                                model=request.model,
                                content=content,
                                raw_response=decoded,
                            )
                    choice_finish_reason = choice.get("finish_reason")
                    if isinstance(choice_finish_reason, str) and choice_finish_reason:
                        finish_reason = choice_finish_reason
                    usage_payload = decoded.get("usage")
                    if isinstance(usage_payload, dict):
                        usage = self._parse_usage(usage_payload)
                        yield LLMStreamEvent(
                            kind="usage",
                            request_id=request.request_id,
                            prompt_version=request.prompt_version,
                            model=request.model,
                            usage=usage,
                            raw_response=decoded,
                        )

                yield LLMStreamEvent(
                    kind="completed",
                    request_id=request.request_id,
                    prompt_version=request.prompt_version,
                    model=request.model,
                    content="".join(content_parts),
                    usage=usage,
                    finish_reason=finish_reason,
                )
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(
                f"DeepSeek request timed out after {self.timeout_seconds:.1f} seconds",
                phase=getattr(exc, "__class__", type(exc)).__name__,
            ) from exc
        except httpx.RequestError as exc:
            raise LLMProviderError(f"DeepSeek request failed: {exc}", retryable=True) from exc

    def _request(self, request: ChatCompletionRequest, *, stream: bool) -> httpx.Response:
        try:
            response = self._client.post(
                "/v1/chat/completions",
                headers=self._auth_headers(),
                json=request.to_payload(stream=stream),
            )
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(
                f"DeepSeek request timed out after {self.timeout_seconds:.1f} seconds",
                phase=getattr(exc, "__class__", type(exc)).__name__,
            ) from exc
        except httpx.RequestError as exc:
            raise LLMProviderError(f"DeepSeek request failed: {exc}", retryable=True) from exc
        self._raise_for_status(response)
        return response

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _raise_for_status(self, response: httpx.Response) -> None:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            detail = exc.response.text.strip()
            if status_code == 429:
                raise LLMRateLimitError(
                    f"DeepSeek request failed with HTTP 429: {detail}",
                ) from exc
            retryable = 500 <= status_code < 600
            raise LLMProviderError(
                f"DeepSeek request failed with HTTP {status_code}: {detail}",
                status_code=status_code,
                retryable=retryable,
            ) from exc

    def _parse_json_response(self, response: httpx.Response) -> dict[str, Any]:
        try:
            data = response.json()
        except ValueError as exc:
            raise LLMProtocolError("DeepSeek returned an invalid JSON payload") from exc
        if not isinstance(data, dict):
            raise LLMProtocolError("DeepSeek returned an invalid JSON payload")
        return data

    def _parse_completion_result(
        self,
        request: ChatCompletionRequest,
        payload: dict[str, Any],
    ) -> ChatCompletionResult:
        choice = self._first_choice(payload)
        message = choice.get("message")
        if not isinstance(message, dict):
            raise LLMProtocolError("DeepSeek returned an invalid message payload")
        content = message.get("content")
        if not isinstance(content, str):
            raise LLMProtocolError("DeepSeek returned an empty reply")
        finish_reason = choice.get("finish_reason")
        usage_payload = payload.get("usage")
        usage = self._parse_usage(usage_payload) if isinstance(usage_payload, dict) else None
        return ChatCompletionResult(
            request_id=request.request_id,
            prompt_version=request.prompt_version,
            model=request.model,
            message=LLMMessage(role="assistant", content=content.strip()),
            finish_reason=finish_reason if isinstance(finish_reason, str) else None,
            usage=usage,
            raw_response=payload,
        )

    @staticmethod
    def _first_choice(payload: dict[str, Any]) -> dict[str, Any]:
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LLMProtocolError("DeepSeek returned no choices")
        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise LLMProtocolError("DeepSeek returned an invalid choice payload")
        return first_choice

    @staticmethod
    def _parse_usage(payload: dict[str, Any]) -> ChatCompletionUsage:
        prompt_tokens = payload.get("prompt_tokens")
        completion_tokens = payload.get("completion_tokens")
        total_tokens = payload.get("total_tokens")
        if not all(isinstance(value, int) for value in (prompt_tokens, completion_tokens, total_tokens)):
            raise LLMProtocolError("DeepSeek returned an invalid usage payload")
        return ChatCompletionUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )
