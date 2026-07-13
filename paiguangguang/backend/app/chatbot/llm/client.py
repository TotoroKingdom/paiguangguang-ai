from __future__ import annotations

from dataclasses import dataclass
import time

from app.chatbot.llm.exceptions import LLMError, LLMProviderError, LLMRateLimitError, LLMTimeoutError
from app.chatbot.llm.provider import ChatCompletionRequest, ChatCompletionResult, LLMProvider, LLMStreamEvent
from app.core.config import Settings, get_settings


@dataclass(frozen=True, slots=True)
class _RetryPolicy:
    max_attempts: int
    initial_backoff_seconds: float = 0.1

    def delay_for_attempt(self, attempt_number: int) -> float:
        return self.initial_backoff_seconds * (2 ** max(attempt_number - 1, 0))


class LLMClient:
    def __init__(
        self,
        provider: LLMProvider,
        settings: Settings | None = None,
        *,
        max_attempts: int | None = None,
        sleep_fn=time.sleep,
    ) -> None:
        self.provider = provider
        self.settings = settings or get_settings()
        attempts = max_attempts if max_attempts is not None else self.settings.chatbot_llm_max_attempts
        self._retry_policy = _RetryPolicy(max_attempts=max(1, attempts))
        self._sleep = sleep_fn

    def close(self) -> None:
        close = getattr(self.provider, "close", None)
        if callable(close):
            close()

    def complete(self, request: ChatCompletionRequest) -> ChatCompletionResult:
        attempt = 1
        while True:
            try:
                return self.provider.complete(request)
            except (LLMTimeoutError, LLMRateLimitError, LLMProviderError) as exc:
                if not self._should_retry(exc, attempt):
                    raise
                self._sleep(self._retry_policy.delay_for_attempt(attempt))
                attempt += 1

    def stream(self, request: ChatCompletionRequest):
        attempt = 1
        while True:
            saw_delta = False
            try:
                for event in self.provider.stream(request):
                    if event.kind == "delta" and event.content:
                        saw_delta = True
                    yield event
                return
            except (LLMTimeoutError, LLMRateLimitError, LLMProviderError) as exc:
                if saw_delta or not self._should_retry(exc, attempt):
                    raise
                self._sleep(self._retry_policy.delay_for_attempt(attempt))
                attempt += 1
            except LLMError:
                raise

    def _should_retry(self, exc: Exception, attempt: int) -> bool:
        if attempt >= self._retry_policy.max_attempts:
            return False
        if isinstance(exc, (LLMTimeoutError, LLMRateLimitError)):
            return True
        if isinstance(exc, LLMProviderError):
            return exc.retryable
        return False
