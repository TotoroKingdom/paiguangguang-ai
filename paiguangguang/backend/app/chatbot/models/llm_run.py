from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKeyConstraint, Index, Integer, String, UniqueConstraint, text as sa_text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ChatbotLLMRun(Base):
    __tablename__ = "chatbot_llm_runs"
    __table_args__ = (
        ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_chatbot_llm_runs_user_id_users", ondelete="CASCADE"),
        ForeignKeyConstraint(
            ["conversation_id"],
            ["chatbot_conversations.id"],
            name="fk_chatbot_llm_runs_conversation_id_chatbot_conversations",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["message_id"],
            ["chatbot_messages.id"],
            name="fk_chatbot_llm_runs_message_id_chatbot_messages",
            ondelete="CASCADE",
        ),
        CheckConstraint("status IN ('pending', 'streaming', 'completed', 'failed', 'cancelled')", name="ck_chatbot_llm_runs_status"),
        CheckConstraint("attempt_count >= 1", name="ck_chatbot_llm_runs_attempt_count"),
        CheckConstraint("prompt_tokens >= 0", name="ck_chatbot_llm_runs_prompt_tokens"),
        CheckConstraint("completion_tokens >= 0", name="ck_chatbot_llm_runs_completion_tokens"),
        CheckConstraint("total_tokens >= 0", name="ck_chatbot_llm_runs_total_tokens"),
        UniqueConstraint("message_id", name="uq_chatbot_llm_runs_message_id"),
        Index("ix_chatbot_llm_runs_request_id", "request_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    request_id: Mapped[str] = mapped_column(String(36), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    conversation_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    message_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", server_default="pending")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=sa_text("1"))
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=sa_text("0"))
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=sa_text("0"))
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=sa_text("0"))
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    first_token_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    finish_reason: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    conversation: Mapped["ChatbotConversation"] = relationship(back_populates="llm_runs", lazy="selectin")
    message: Mapped["ChatbotMessage"] = relationship(back_populates="llm_run", lazy="selectin")
