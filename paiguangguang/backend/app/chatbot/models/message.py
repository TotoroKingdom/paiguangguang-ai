from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKeyConstraint, Index, Integer, JSON, String, Text, UniqueConstraint, text as sa_text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ChatbotMessage(Base):
    __tablename__ = "chatbot_messages"
    __table_args__ = (
        ForeignKeyConstraint(
            ["conversation_id"],
            ["chatbot_conversations.id"],
            name="fk_chatbot_messages_conversation_id_chatbot_conversations",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_chatbot_messages_user_id_users", ondelete="CASCADE"),
        ForeignKeyConstraint(
            ["parent_message_id"],
            ["chatbot_messages.id"],
            name="fk_chatbot_messages_parent_message_id_chatbot_messages",
            ondelete="SET NULL",
        ),
        UniqueConstraint("conversation_id", "sequence_number", name="uq_chatbot_messages_conversation_id_sequence_number"),
        UniqueConstraint(
            "user_id",
            "conversation_id",
            "client_request_id",
            name="uq_chatbot_messages_user_id_conversation_id_client_request_id",
        ),
        CheckConstraint("role IN ('user', 'assistant', 'system', 'tool')", name="ck_chatbot_messages_role"),
        CheckConstraint("status IN ('pending', 'streaming', 'completed', 'failed', 'cancelled')", name="ck_chatbot_messages_status"),
        CheckConstraint("sequence_number >= 1", name="ck_chatbot_messages_sequence_number"),
        CheckConstraint("prompt_tokens >= 0", name="ck_chatbot_messages_prompt_tokens"),
        CheckConstraint("completion_tokens >= 0", name="ck_chatbot_messages_completion_tokens"),
        CheckConstraint("total_tokens >= 0", name="ck_chatbot_messages_total_tokens"),
        Index("ix_chatbot_messages_conversation_id_sequence_number", "conversation_id", sa_text("sequence_number DESC")),
        Index("ix_chatbot_messages_user_id_status_updated_at", "user_id", "status", sa_text("updated_at DESC")),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    conversation_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    content_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", server_default="pending")
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    parent_message_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    client_request_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=sa_text("0"))
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=sa_text("0"))
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=sa_text("0"))
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    conversation: Mapped["ChatbotConversation"] = relationship(back_populates="messages", lazy="selectin")
    parent_message: Mapped["ChatbotMessage | None"] = relationship(
        back_populates="child_messages",
        remote_side=lambda: [ChatbotMessage.id],
        foreign_keys=lambda: [ChatbotMessage.parent_message_id],
        lazy="selectin",
    )
    child_messages: Mapped[list["ChatbotMessage"]] = relationship(
        back_populates="parent_message",
        foreign_keys=lambda: [ChatbotMessage.parent_message_id],
        lazy="selectin",
    )
    llm_run: Mapped["ChatbotLLMRun | None"] = relationship(back_populates="message", uselist=False, lazy="selectin")
