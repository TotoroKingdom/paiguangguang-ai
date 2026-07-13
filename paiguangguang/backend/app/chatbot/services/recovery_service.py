from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Iterator

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.models.llm_run import ChatbotLLMRun
from app.chatbot.models.message import ChatbotMessage
from app.chatbot.observability import log_chatbot_event
from app.core.config import Settings, get_settings
from app.db.session import build_session_factory


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RecoveryService:
    def __init__(
        self,
        session_factory: sessionmaker[Session] | None = None,
        *,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.session_factory = session_factory or build_session_factory(self.settings)

    @contextmanager
    def _session(self) -> Iterator[Session]:
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def reap_stale_runs(self, *, limit: int = 100) -> int:
        if limit < 1:
            raise ValueError("limit must be positive")

        stale_before = _utcnow() - timedelta(seconds=self.settings.chatbot_stale_run_seconds)
        recovered = 0
        with self._session() as session:
            stale_runs = list(
                session.scalars(
                    select(ChatbotLLMRun)
                    .where(
                        ChatbotLLMRun.status.in_(("pending", "streaming")),
                        ChatbotLLMRun.updated_at < stale_before,
                    )
                    .order_by(ChatbotLLMRun.updated_at.asc(), ChatbotLLMRun.id.asc())
                    .limit(limit)
                )
            )
            now = _utcnow()
            for run in stale_runs:
                message = session.get(ChatbotMessage, run.message_id)
                if message is not None:
                    message.status = "failed"
                    message.error_code = "CHATBOT_STALE_GENERATION"
                    message.updated_at = now
                run.status = "failed"
                run.error_code = "CHATBOT_STALE_GENERATION"
                run.error_message = "Generation expired before completion"
                run.completed_at = now
                run.updated_at = now
                recovered += 1
        if recovered:
            log_chatbot_event(
                "chatbot.recovery.stale_runs",
                hits=recovered,
                status="failed",
                source="postgres",
            )
        return recovered


_RECOVERY_SERVICE: RecoveryService | None = None


def get_recovery_service() -> RecoveryService:
    global _RECOVERY_SERVICE
    if _RECOVERY_SERVICE is None:
        _RECOVERY_SERVICE = RecoveryService()
    return _RECOVERY_SERVICE
