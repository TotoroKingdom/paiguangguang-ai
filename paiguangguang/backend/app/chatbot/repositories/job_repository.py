from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.models.job import ChatbotJob


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class JobRecord:
    id: str
    kind: str
    dedup_key: str
    payload: dict[str, object]
    status: str
    attempt_count: int


class JobRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    @staticmethod
    def _record(row: ChatbotJob) -> JobRecord:
        return JobRecord(
            id=row.id,
            kind=row.kind,
            dedup_key=row.dedup_key,
            payload=dict(row.payload or {}),
            status=row.status,
            attempt_count=row.attempt_count,
        )

    def enqueue(
        self,
        session: Session,
        *,
        kind: str,
        dedup_key: str,
        payload: dict[str, object],
    ) -> ChatbotJob:
        existing = session.scalar(select(ChatbotJob).where(ChatbotJob.dedup_key == dedup_key))
        if existing is not None:
            return existing
        row = ChatbotJob(kind=kind, dedup_key=dedup_key, payload=dict(payload), status="pending")
        try:
            with session.begin_nested():
                session.add(row)
                session.flush()
        except IntegrityError:
            winner = session.scalar(select(ChatbotJob).where(ChatbotJob.dedup_key == dedup_key))
            if winner is None:
                raise
            return winner
        return row

    def claim_batch(self, *, limit: int = 20) -> list[JobRecord]:
        if limit < 1:
            raise ValueError("limit must be positive")
        now = _utcnow()
        with self.session_factory() as session:
            rows = list(
                session.scalars(
                    select(ChatbotJob)
                    .where(
                        ChatbotJob.status.in_(("pending", "retry")),
                        ChatbotJob.available_at <= now,
                    )
                    .order_by(ChatbotJob.available_at.asc(), ChatbotJob.id.asc())
                    .limit(limit)
                    .with_for_update(skip_locked=True)
                )
            )
            for row in rows:
                row.status = "running"
                row.attempt_count += 1
                row.locked_at = now
                row.updated_at = now
            session.commit()
            return [self._record(row) for row in rows]

    def mark_completed(self, job_id: str) -> None:
        now = _utcnow()
        with self.session_factory() as session:
            session.execute(
                update(ChatbotJob)
                .where(ChatbotJob.id == job_id, ChatbotJob.status == "running")
                .values(
                    status="completed",
                    completed_at=now,
                    locked_at=None,
                    last_error=None,
                    updated_at=now,
                )
            )
            session.commit()

    def mark_retry(
        self,
        job_id: str,
        *,
        error: str,
        delay_seconds: int,
        max_attempts: int,
    ) -> None:
        now = _utcnow()
        with self.session_factory() as session:
            row = session.get(ChatbotJob, job_id)
            if row is None or row.status != "running":
                return
            row.status = "failed" if row.attempt_count >= max_attempts else "retry"
            row.available_at = now + timedelta(seconds=max(0, delay_seconds))
            row.locked_at = None
            row.last_error = error[:500]
            row.updated_at = now
            session.commit()

    def recover_stale(self, *, stale_seconds: int) -> int:
        now = _utcnow()
        cutoff = now - timedelta(seconds=max(1, stale_seconds))
        with self.session_factory() as session:
            result = session.execute(
                update(ChatbotJob)
                .where(ChatbotJob.status == "running", ChatbotJob.locked_at < cutoff)
                .values(status="retry", available_at=now, locked_at=None, updated_at=now)
            )
            session.commit()
            return int(result.rowcount or 0)
