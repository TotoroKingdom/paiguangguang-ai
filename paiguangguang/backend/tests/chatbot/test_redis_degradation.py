from __future__ import annotations

from app.chatbot.services.cancellation_service import CancellationService
from app.chatbot.services.concurrency_service import ConcurrencyService
from app.core.config import Settings


class FakeRedisClient:
    def __init__(self, fail: set[str]) -> None:
        self.fail = set(fail)
        self.values: dict[str, str] = {}

    def _check(self, operation: str) -> None:
        if operation in self.fail:
            raise RuntimeError(f"redis {operation} unavailable")

    def ping(self) -> None:
        self._check("ping")

    def get(self, key: str):
        self._check("get")
        return self.values.get(key)

    def set(self, key: str, value: str, **kwargs):
        self._check("set")
        if kwargs.get("nx") and key in self.values:
            return False
        self.values[key] = value
        return True

    def eval(self, script: str, key_count: int, key: str, owner: str, *args):
        self._check("eval")
        if self.values.get(key) != owner:
            return 0
        if "del" in script:
            self.values.pop(key, None)
        return 1

    def delete(self, key: str):
        self._check("delete")
        return int(self.values.pop(key, None) is not None)


class FakeRedisModule:
    def __init__(self, fail: set[str]) -> None:
        self.client = FakeRedisClient(fail)

    def from_url(self, url: str, decode_responses: bool):
        return self.client


def _redis_settings() -> Settings:
    return Settings(redis_url="redis://example.invalid/0", chatbot_lock_ttl_seconds=90)


def test_cancellation_initialization_degrades_when_ping_fails() -> None:
    service = CancellationService(
        settings=_redis_settings(),
        redis_module=FakeRedisModule(fail={"ping"}),
    )
    record = service.request_stop("conv-1", "assistant-1")
    assert record.status == "cancellation_requested"
    assert service.is_requested("conv-1", "assistant-1") is True


def test_cancellation_falls_back_when_redis_fails_mid_request() -> None:
    service = CancellationService(
        settings=_redis_settings(),
        redis_module=FakeRedisModule(fail={"set"}),
    )
    record = service.request_stop("conv-1", "assistant-1")
    assert record.status == "cancellation_requested"
    assert service.is_requested("conv-1", "assistant-1") is True


def test_concurrency_falls_back_and_release_never_raises() -> None:
    module = FakeRedisModule(fail={"set"})
    service = ConcurrencyService(settings=_redis_settings(), redis_module=module)
    lease = service.acquire("conv-1", "user-1")
    assert lease is not None
    assert lease.backend == "memory"
    assert service.release(lease) is True

    redis_module = FakeRedisModule(fail=set())
    redis_service = ConcurrencyService(settings=_redis_settings(), redis_module=redis_module)
    redis_lease = redis_service.acquire("conv-2", "user-1")
    assert redis_lease is not None
    assert redis_lease.backend == "redis"
    redis_module.client.fail = {"eval"}
    assert redis_service.release(redis_lease) is False
