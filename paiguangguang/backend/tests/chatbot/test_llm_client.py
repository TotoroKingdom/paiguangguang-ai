from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.chatbot.llm.client import LLMClient
from app.chatbot.llm.exceptions import LLMRateLimitError, LLMTimeoutError
from app.chatbot.llm.provider import ChatCompletionRequest, ChatCompletionResult, ChatCompletionUsage, LLMMessage, LLMStreamEvent
from app.core.config import Settings


@dataclass
class _FakeProvider:
    complete_attempts: int = 0
    stream_attempts: int = 0
    complete_failures: list[Exception] | None = None
    stream_outcomes: list[tuple[list[LLMStreamEvent], Exception | None]] | None = None

    def complete(self, request: ChatCompletionRequest) -> ChatCompletionResult:
        self.complete_attempts += 1
        if self.complete_failures:
            failure = self.complete_failures.pop(0)
            raise failure
        return ChatCompletionResult(
            request_id=request.request_id,
            prompt_version=request.prompt_version,
            model=request.model,
            message=LLMMessage(role="assistant", content="done"),
            finish_reason="stop",
            usage=ChatCompletionUsage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
        )

    def stream(self, request: ChatCompletionRequest):
        self.stream_attempts += 1
        if self.stream_outcomes:
            events, error = self.stream_outcomes.pop(0)
            for event in events:
                yield event
            if error is not None:
                raise error
            return
        yield LLMStreamEvent(
            kind="delta",
            request_id=request.request_id,
            prompt_version=request.prompt_version,
            model=request.model,
            content="hello",
        )
        yield LLMStreamEvent(
            kind="completed",
            request_id=request.request_id,
            prompt_version=request.prompt_version,
            model=request.model,
            content="hello",
            finish_reason="stop",
        )

    def close(self) -> None:
        return None


def _request() -> ChatCompletionRequest:
    return ChatCompletionRequest(
        request_id="req-1",
        prompt_version="chatbot-v1",
        model="deepseek-chat",
        messages=(LLMMessage(role="user", content="Hello"),),
    )


def test_llm_client_retries_complete_when_error_is_retryable() -> None:
    provider = _FakeProvider(complete_failures=[LLMRateLimitError("rate limited")])
    client = LLMClient(provider=provider, settings=Settings(chatbot_llm_max_attempts=2))

    result = client.complete(_request())

    assert provider.complete_attempts == 2
    assert result.message.content == "done"


def test_llm_client_retries_stream_before_first_delta() -> None:
    provider = _FakeProvider(stream_outcomes=[([], LLMRateLimitError("rate limited"))])
    client = LLMClient(provider=provider, settings=Settings(chatbot_llm_max_attempts=2))

    events = list(client.stream(_request()))

    assert provider.stream_attempts == 2
    assert [event.kind for event in events] == ["delta", "completed"]


def test_llm_client_does_not_retry_stream_after_delta() -> None:
    provider = _FakeProvider(
        stream_outcomes=[
            (
                [
                    LLMStreamEvent(
                        kind="delta",
                        request_id="req-1",
                        prompt_version="chatbot-v1",
                        model="deepseek-chat",
                        content="hello",
                    ),
                ],
                LLMRateLimitError("rate limited after delta"),
            ),
        ]
    )
    client = LLMClient(provider=provider, settings=Settings(chatbot_llm_max_attempts=2))

    iterator = client.stream(_request())
    first_event = next(iterator)
    assert first_event.kind == "delta"

    with pytest.raises(LLMRateLimitError):
        list(iterator)

    assert provider.stream_attempts == 1


def test_llm_client_maps_timeout_and_uses_settings_for_attempts() -> None:
    provider = _FakeProvider(complete_failures=[LLMTimeoutError("request timed out")])
    client = LLMClient(provider=provider, settings=Settings(chatbot_llm_max_attempts=1))

    with pytest.raises(LLMTimeoutError):
        client.complete(_request())

    assert provider.complete_attempts == 1
