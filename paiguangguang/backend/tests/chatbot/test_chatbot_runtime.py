from __future__ import annotations

import asyncio

from app.chatbot.services.runtime import ChatbotRuntime
from app.core.config import Settings


class FakeRecovery:
    def __init__(self) -> None:
        self.calls = 0

    def reap_stale_runs(self) -> int:
        self.calls += 1
        return 0


class FakeJobs:
    def __init__(self) -> None:
        self.recovered = 0
        self.runs = 0

    def recover_stale(self, *, stale_seconds: int) -> int:
        self.recovered += 1
        return 0

    def run_once(self, *, limit: int) -> int:
        self.runs += 1
        return 0

    def close(self) -> None:
        return None


def test_runtime_runs_startup_iteration_and_stops() -> None:
    recovery = FakeRecovery()
    jobs = FakeJobs()
    runtime = ChatbotRuntime(
        recovery_service=recovery,
        job_runner=jobs,
        settings=Settings(chatbot_worker_interval_seconds=3600),
    )

    async def scenario() -> None:
        await runtime.start()
        await asyncio.sleep(0)
        await runtime.stop()

    asyncio.run(scenario())
    assert recovery.calls >= 1
    assert jobs.recovered == 1
    assert jobs.runs >= 1
