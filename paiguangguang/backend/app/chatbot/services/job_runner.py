from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.chatbot.memory.conversation_summary import ConversationSummaryService
from app.chatbot.memory.short_term_memory import ShortTermMemoryService
from app.chatbot.repositories.job_repository import JobRepository
from app.chatbot.services.completion_jobs import ConversationTitleService
from app.chatbot.services.memory_service import MemoryService
from app.core.config import Settings, get_settings


class JobRunner:
    def __init__(
        self,
        *,
        repository: JobRepository,
        memory_service: MemoryService,
        short_term_memory: ShortTermMemoryService,
        conversation_summary: ConversationSummaryService,
        title_service: ConversationTitleService,
        cleanup_service: Any,
        settings: Settings | None = None,
        close_callback: Callable[[], None] | None = None,
    ) -> None:
        self.repository = repository
        self.memory_service = memory_service
        self.short_term_memory = short_term_memory
        self.conversation_summary = conversation_summary
        self.title_service = title_service
        self.cleanup_service = cleanup_service
        self.settings = settings or get_settings()
        self._close_callback = close_callback

    def recover_stale(self, *, stale_seconds: int) -> int:
        return self.repository.recover_stale(stale_seconds=stale_seconds)

    def run_once(self, *, limit: int) -> int:
        jobs = self.repository.claim_batch(limit=limit)
        for job in jobs:
            try:
                if job.kind == "completed_turn_memory":
                    self.memory_service.process_completed_turn(
                        str(job.payload["user_id"]),
                        str(job.payload["conversation_id"]),
                        str(job.payload["user_message_id"]),
                        str(job.payload["assistant_message_id"]),
                    )
                elif job.kind == "refresh_conversation_context":
                    self.short_term_memory.refresh_context(
                        str(job.payload["user_id"]),
                        str(job.payload["conversation_id"]),
                    )
                    self.conversation_summary.maybe_generate_summary(
                        str(job.payload["user_id"]),
                        str(job.payload["conversation_id"]),
                    )
                elif job.kind == "auto_title":
                    self.title_service.apply_auto_title(job.payload)
                elif job.kind == "cleanup_conversation":
                    self.cleanup_service.cleanup_conversation(job.payload)
                elif job.kind == "cleanup_memory":
                    self.cleanup_service.cleanup_memory(job.payload)
                else:
                    raise ValueError(f"Unsupported chatbot job kind: {job.kind}")
            except Exception as exc:
                if job.kind.startswith("cleanup_"):
                    self.cleanup_service.mark_retry(job.payload)
                delay = min(300, 2**job.attempt_count)
                self.repository.mark_retry(
                    job.id,
                    error=f"{type(exc).__name__}: {str(exc)[:440]}",
                    delay_seconds=delay,
                    max_attempts=self.settings.chatbot_job_max_attempts,
                )
            else:
                self.repository.mark_completed(job.id)
        return len(jobs)

    def close(self) -> None:
        if self._close_callback is not None:
            self._close_callback()
