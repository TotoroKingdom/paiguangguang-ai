from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.models.job import ChatbotJob
from app.chatbot.repositories.job_repository import JobRepository
from app.db.base import Base


def _factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_engine(
        f"sqlite+pysqlite:///{(tmp_path / f'{uuid4()}.sqlite3').as_posix()}",
        future=True,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def test_job_repository_deduplicates_claims_and_completes(tmp_path) -> None:
    factory = _factory(tmp_path)
    repository = JobRepository(factory)
    with factory() as session:
        first = repository.enqueue(
            session,
            kind="completed_turn_memory",
            dedup_key="memory:user-message-1",
            payload={"user_message_id": "user-message-1"},
        )
        second = repository.enqueue(
            session,
            kind="completed_turn_memory",
            dedup_key="memory:user-message-1",
            payload={"user_message_id": "user-message-1"},
        )
        session.commit()

    assert first.id == second.id
    claimed = repository.claim_batch(limit=10)
    assert [item.id for item in claimed] == [first.id]
    assert claimed[0].status == "running"
    assert claimed[0].attempt_count == 1

    repository.mark_completed(first.id)
    with factory() as session:
        row = session.scalar(select(ChatbotJob).where(ChatbotJob.id == first.id))
    assert row is not None
    assert row.status == "completed"
    assert repository.claim_batch(limit=10) == []


def test_job_repository_retries_then_fails_at_max_attempts(tmp_path) -> None:
    factory = _factory(tmp_path)
    repository = JobRepository(factory)
    with factory() as session:
        job = repository.enqueue(
            session,
            kind="cleanup_memory",
            dedup_key="cleanup-memory:1",
            payload={"memory_id": "1"},
        )
        session.commit()

    repository.claim_batch(limit=1)
    repository.mark_retry(
        job.id,
        error="RuntimeError: unavailable",
        delay_seconds=0,
        max_attempts=2,
    )
    assert repository.claim_batch(limit=1)[0].attempt_count == 2
    repository.mark_retry(
        job.id,
        error="RuntimeError: unavailable",
        delay_seconds=0,
        max_attempts=2,
    )

    with factory() as session:
        row = session.get(ChatbotJob, job.id)
    assert row is not None
    assert row.status == "failed"
