from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from threading import Lock
from time import monotonic

from app.core.errors import ServiceRateLimitError


@dataclass(frozen=True)
class RateLimitConfig:
    max_requests: int
    window_seconds: int


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = {}
        self._lock = Lock()

    def check(self, key: str, config: RateLimitConfig, *, operation: str) -> None:
        now = monotonic()
        window_start = now - config.window_seconds
        with self._lock:
            events = self._events.setdefault(key, deque())
            while events and events[0] < window_start:
                events.popleft()
            if len(events) >= config.max_requests:
                raise ServiceRateLimitError(operation=operation, limit=config.max_requests, window_seconds=config.window_seconds)
            events.append(now)


_RATE_LIMITER = InMemoryRateLimiter()


def get_rate_limiter() -> InMemoryRateLimiter:
    return _RATE_LIMITER
