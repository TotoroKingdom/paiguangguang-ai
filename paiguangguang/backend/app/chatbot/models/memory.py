from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKeyConstraint, Index, JSON, String, Text, text as sa_text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ChatbotMemory(Base):
    __tablename__ = "chatbot_memories"
    __table_args__ = (
        ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_chatbot_memories_user_id_users", ondelete="CASCADE"),
        ForeignKeyConstraint(
            ["conversation_id"],
            ["chatbot_conversations.id"],
            name="fk_chatbot_memories_conversation_id_chatbot_conversations",
            ondelete="SET NULL",
        ),
        CheckConstraint(
            "memory_type IN ('preference', 'goal', 'project_context', 'explicit', 'fact', 'work_context')",
            name="ck_chatbot_memories_memory_type",
        ),
        CheckConstraint("status IN ('candidate', 'active', 'superseded', 'deleted', 'failed')", name="ck_chatbot_memories_status"),
        CheckConstraint("embedding_status IN ('pending', 'indexed', 'failed', 'deleted')", name="ck_chatbot_memories_embedding_status"),
        CheckConstraint("importance >= 0.0 AND importance <= 1.0", name="ck_chatbot_memories_importance"),
        CheckConstraint("confidence >= 0.0 AND confidence <= 1.0", name="ck_chatbot_memories_confidence"),
        Index("ix_chatbot_memories_user_id_status_updated_at_id", "user_id", "status", sa_text("updated_at DESC"), sa_text("id DESC")),
        Index("ix_chatbot_memories_user_id_normalized_hash", "user_id", "normalized_hash"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    memory_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    importance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default=sa_text("0"))
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default=sa_text("0"))
    source_message_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="candidate", server_default="candidate")
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    normalized_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", server_default="pending")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    conversation: Mapped["ChatbotConversation | None"] = relationship(back_populates="memories", lazy="selectin")
