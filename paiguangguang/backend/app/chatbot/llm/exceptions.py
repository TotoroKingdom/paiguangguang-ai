from __future__ import annotations


class LLMError(RuntimeError):
    """Base class for provider-neutral LLM failures."""


class LLMConfigurationError(ValueError):
    """Raised when the LLM layer is misconfigured."""


class LLMProviderError(LLMError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


class LLMRateLimitError(LLMProviderError):
    def __init__(self, message: str = "LLM request was rate limited", *, retry_after_seconds: float | None = None) -> None:
        super().__init__(message, status_code=429, retryable=True)
        self.retry_after_seconds = retry_after_seconds


class LLMTimeoutError(LLMProviderError):
    def __init__(self, message: str, *, phase: str | None = None) -> None:
        super().__init__(message, status_code=None, retryable=True)
        self.phase = phase


class LLMProtocolError(LLMError):
    """Raised when the provider returns malformed or unsupported payloads."""
