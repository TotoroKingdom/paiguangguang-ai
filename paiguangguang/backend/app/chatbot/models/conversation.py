from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKeyConstraint, Index, Integer, String, Text, UniqueConstraint, text as sa_text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ChatbotConversation(Base):
    __tablename__ = "chatbot_conversations"
    __table_args__ = (
        ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_chatbot_conversations_user_id_users", ondelete="CASCADE"),
        CheckConstraint("status IN ('active', 'archived', 'deleted')", name="ck_chatbot_conversations_status"),
        CheckConstraint("title_source IN ('default', 'auto', 'manual')", name="ck_chatbot_conversations_title_source"),
        CheckConstraint("next_sequence >= 1", name="ck_chatbot_conversations_next_sequence"),
        CheckConstraint(
            "cleanup_status IN ('pending', 'completed', 'retry')",
            name="ck_chatbot_conversations_cleanup_status",
        ),
        Index("ix_chatbot_conversations_user_id_status_last_message_at_id", "user_id", "status", sa_text("last_message_at DESC"), sa_text("id DESC")),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    title_source: Mapped[str] = mapped_column(String(20), nullable=False, default="default", server_default="default")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", server_default="active")
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    system_prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    next_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=sa_text("1"))
    last_message_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    cleanup_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    messages: Mapped[list["ChatbotMessage"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )
    summaries: Mapped[list["ChatbotConversationSummary"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )
    memories: Mapped[list["ChatbotMemory"]] = relationship(
        back_populates="conversation",
        lazy="selectin",
    )
    llm_runs: Mapped[list["ChatbotLLMRun"]] = relationship(
        back_populates="conversation",
        lazy="selectin",
    )


class ChatbotConversationSummary(Base):
    __tablename__ = "chatbot_conversation_summaries"
    __table_args__ = (
        ForeignKeyConstraint(
            ["conversation_id"],
            ["chatbot_conversations.id"],
            name="fk_chatbot_conversation_summaries_conversation_id_chatbot_conversations",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "conversation_id",
            "summary_version",
            name="uq_chatbot_conversation_summaries_conversation_id_summary_version",
        ),
        CheckConstraint("start_sequence >= 1", name="ck_chatbot_conversation_summaries_start_sequence"),
        CheckConstraint("end_sequence >= 1", name="ck_chatbot_conversation_summaries_end_sequence"),
        CheckConstraint("end_sequence >= start_sequence", name="ck_chatbot_conversation_summaries_sequence_order"),
        CheckConstraint("summary_version >= 1", name="ck_chatbot_conversation_summaries_summary_version"),
        CheckConstraint("token_count >= 0", name="ck_chatbot_conversation_summaries_token_count"),
        CheckConstraint("status IN ('pending', 'completed', 'failed')", name="ck_chatbot_conversation_summaries_status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    conversation_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    start_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    end_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    summary_version: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=sa_text("0"))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", server_default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    conversation: Mapped["ChatbotConversation"] = relationship(back_populates="summaries", lazy="selectin")
