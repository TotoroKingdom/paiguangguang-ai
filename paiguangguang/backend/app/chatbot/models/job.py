from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
    text as sa_text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ChatbotJob(Base):
    __tablename__ = "chatbot_jobs"
    __table_args__ = (
        UniqueConstraint("dedup_key", name="uq_chatbot_jobs_dedup_key"),
        CheckConstraint(
            "kind IN ('completed_turn_memory', 'refresh_conversation_context', "
            "'auto_title', 'cleanup_conversation', 'cleanup_memory')",
            name="ck_chatbot_jobs_kind",
        ),
        CheckConstraint(
            "status IN ('pending', 'running', 'retry', 'completed', 'failed')",
            name="ck_chatbot_jobs_status",
        ),
        CheckConstraint("attempt_count >= 0", name="ck_chatbot_jobs_attempt_count"),
        Index("ix_chatbot_jobs_status_available_at_id", "status", "available_at", "id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    kind: Mapped[str] = mapped_column(String(50), nullable=False)
    dedup_key: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", server_default="pending"
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sa_text("0")
    )
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )
