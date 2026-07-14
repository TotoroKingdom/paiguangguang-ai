from __future__ import annotations

import asyncio

from app.chatbot.llm.client import LLMClient
from app.chatbot.llm.deepseek_provider import DeepSeekProvider
from app.chatbot.memory.conversation_summary import ConversationSummaryService
from app.chatbot.memory.short_term_memory import ShortTermMemoryService
from app.chatbot.repositories.job_repository import JobRepository
from app.chatbot.services.completion_jobs import ConversationTitleService
from app.chatbot.services.job_runner import JobRunner
from app.chatbot.services.memory_service import MemoryService
from app.chatbot.services.recovery_service import RecoveryService
from app.core.config import Settings, get_settings
from app.db.session import build_session_factory


class ChatbotRuntime:
    def __init__(self, *, recovery_service, job_runner, settings=None) -> None:
        self.settings = settings or get_settings()
        self.recovery_service = recovery_service
        self.job_runner = job_runner
        self._stop = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

    async def run_iteration(self) -> None:
        await asyncio.to_thread(self.recovery_service.reap_stale_runs)
        await asyncio.to_thread(
            self.job_runner.run_once,
            limit=self.settings.chatbot_job_batch_size,
        )

    async def _loop(self) -> None:
        while not self._stop.is_set():
            await self.run_iteration()
            try:
                await asyncio.wait_for(
                    self._stop.wait(),
                    timeout=max(1, self.settings.chatbot_worker_interval_seconds),
                )
            except TimeoutError:
                continue

    async def start(self) -> None:
        await asyncio.to_thread(
            self.job_runner.recover_stale,
            stale_seconds=self.settings.chatbot_job_stale_seconds,
        )
        self._stop.clear()
        self._task = asyncio.create_task(self._loop(), name="chatbot-runtime")

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            await self._task
            self._task = None
        await asyncio.to_thread(self.job_runner.close)


def build_chatbot_runtime(settings: Settings | None = None) -> ChatbotRuntime:
    from app.chatbot.services.cleanup_service import CleanupService

    settings = settings or get_settings()
    session_factory = build_session_factory(settings)
    repository = JobRepository(session_factory)
    llm_client = LLMClient(
        provider=DeepSeekProvider(settings=settings),
        settings=settings,
    )
    short_term_memory = ShortTermMemoryService(session_factory, settings=settings)
    memory_service = MemoryService(
        session_factory=session_factory,
        llm_client=llm_client,
        settings=settings,
    )
    summary_service = ConversationSummaryService(
        session_factory,
        llm_client=llm_client,
        settings=settings,
    )
    cleanup_service = CleanupService(
        session_factory=session_factory,
        short_term_memory=short_term_memory,
        settings=settings,
    )
    runner = JobRunner(
        repository=repository,
        memory_service=memory_service,
        short_term_memory=short_term_memory,
        conversation_summary=summary_service,
        title_service=ConversationTitleService(session_factory),
        cleanup_service=cleanup_service,
        settings=settings,
        close_callback=llm_client.close,
    )
    return ChatbotRuntime(
        recovery_service=RecoveryService(session_factory, settings=settings),
        job_runner=runner,
        settings=settings,
    )
