"""create chatbot tables

Revision ID: 0006_create_chatbot_tables
Revises: 0005_add_orig_filename_kb_state
Create Date: 2026-07-13 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0006_create_chatbot_tables"
down_revision = "0005_add_orig_filename_kb_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chatbot_conversations",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("title_source", sa.String(length=20), nullable=False, server_default=sa.text("'default'")),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'active'")),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("system_prompt_version", sa.String(length=50), nullable=False),
        sa.Column("next_sequence", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cleanup_status", sa.String(length=20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_chatbot_conversations_user_id_users", ondelete="CASCADE"),
        sa.CheckConstraint("status IN ('active', 'archived', 'deleted')", name="ck_chatbot_conversations_status"),
        sa.CheckConstraint("title_source IN ('default', 'auto', 'manual')", name="ck_chatbot_conversations_title_source"),
        sa.CheckConstraint("next_sequence >= 1", name="ck_chatbot_conversations_next_sequence"),
        sa.CheckConstraint("cleanup_status IN ('pending', 'completed', 'retry')", name="ck_chatbot_conversations_cleanup_status"),
    )
    op.create_index("ix_chatbot_conversations_user_id", "chatbot_conversations", ["user_id"], unique=False)
    op.create_index("ix_chatbot_conversations_deleted_at", "chatbot_conversations", ["deleted_at"], unique=False)
    op.create_index(
        "ix_chatbot_conversations_user_id_status_last_message_at_id",
        "chatbot_conversations",
        ["user_id", "status", "last_message_at", "id"],
        unique=False,
    )

    op.create_table(
        "chatbot_conversation_summaries",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("conversation_id", sa.String(length=36), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("start_sequence", sa.Integer(), nullable=False),
        sa.Column("end_sequence", sa.Integer(), nullable=False),
        sa.Column("summary_version", sa.Integer(), nullable=False),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["chatbot_conversations.id"],
            name="fk_chatbot_summaries_conversation",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "conversation_id",
            "summary_version",
            name="uq_chatbot_summaries_conversation_version",
        ),
        sa.CheckConstraint("start_sequence >= 1", name="ck_chatbot_conversation_summaries_start_sequence"),
        sa.CheckConstraint("end_sequence >= 1", name="ck_chatbot_conversation_summaries_end_sequence"),
        sa.CheckConstraint("end_sequence >= start_sequence", name="ck_chatbot_conversation_summaries_sequence_order"),
        sa.CheckConstraint("summary_version >= 1", name="ck_chatbot_conversation_summaries_summary_version"),
        sa.CheckConstraint("token_count >= 0", name="ck_chatbot_conversation_summaries_token_count"),
        sa.CheckConstraint("status IN ('pending', 'completed', 'failed')", name="ck_chatbot_conversation_summaries_status"),
    )
    op.create_index(
        "ix_chatbot_conversation_summaries_conversation_id",
        "chatbot_conversation_summaries",
        ["conversation_id"],
        unique=False,
    )

    op.create_table(
        "chatbot_messages",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("conversation_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("content_json", sa.JSON(), nullable=True),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("parent_message_id", sa.String(length=36), nullable=True),
        sa.Column("client_request_id", sa.String(length=36), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["chatbot_conversations.id"],
            name="fk_chatbot_messages_conversation_id_chatbot_conversations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_chatbot_messages_user_id_users", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["parent_message_id"],
            ["chatbot_messages.id"],
            name="fk_chatbot_messages_parent_message_id_chatbot_messages",
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint("conversation_id", "sequence_number", name="uq_chatbot_messages_conversation_id_sequence_number"),
        sa.UniqueConstraint(
            "user_id",
            "conversation_id",
            "client_request_id",
            name="uq_chatbot_messages_user_id_conversation_id_client_request_id",
        ),
        sa.CheckConstraint("role IN ('user', 'assistant', 'system', 'tool')", name="ck_chatbot_messages_role"),
        sa.CheckConstraint("status IN ('pending', 'streaming', 'completed', 'failed', 'cancelled')", name="ck_chatbot_messages_status"),
        sa.CheckConstraint("sequence_number >= 1", name="ck_chatbot_messages_sequence_number"),
        sa.CheckConstraint("prompt_tokens >= 0", name="ck_chatbot_messages_prompt_tokens"),
        sa.CheckConstraint("completion_tokens >= 0", name="ck_chatbot_messages_completion_tokens"),
        sa.CheckConstraint("total_tokens >= 0", name="ck_chatbot_messages_total_tokens"),
    )
    op.create_index("ix_chatbot_messages_conversation_id", "chatbot_messages", ["conversation_id"], unique=False)
    op.create_index("ix_chatbot_messages_user_id", "chatbot_messages", ["user_id"], unique=False)
    op.create_index("ix_chatbot_messages_parent_message_id", "chatbot_messages", ["parent_message_id"], unique=False)
    op.create_index(
        "ix_chatbot_messages_conversation_id_sequence_number",
        "chatbot_messages",
        ["conversation_id", "sequence_number"],
        unique=False,
    )
    op.create_index("ix_chatbot_messages_user_id_status_updated_at", "chatbot_messages", ["user_id", "status", "updated_at"], unique=False)

    op.create_table(
        "chatbot_memories",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("conversation_id", sa.String(length=36), nullable=True),
        sa.Column("memory_type", sa.String(length=50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("importance", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("confidence", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("source_message_ids", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'candidate'")),
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("normalized_hash", sa.String(length=64), nullable=False),
        sa.Column("embedding_status", sa.String(length=20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_chatbot_memories_user_id_users", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["chatbot_conversations.id"],
            name="fk_chatbot_memories_conversation_id_chatbot_conversations",
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "memory_type IN ('preference', 'goal', 'project_context', 'explicit', 'fact', 'work_context')",
            name="ck_chatbot_memories_memory_type",
        ),
        sa.CheckConstraint("status IN ('candidate', 'active', 'superseded', 'deleted', 'failed')", name="ck_chatbot_memories_status"),
        sa.CheckConstraint("embedding_status IN ('pending', 'indexed', 'failed', 'deleted')", name="ck_chatbot_memories_embedding_status"),
        sa.CheckConstraint("importance >= 0.0 AND importance <= 1.0", name="ck_chatbot_memories_importance"),
        sa.CheckConstraint("confidence >= 0.0 AND confidence <= 1.0", name="ck_chatbot_memories_confidence"),
    )
    op.create_index("ix_chatbot_memories_user_id", "chatbot_memories", ["user_id"], unique=False)
    op.create_index("ix_chatbot_memories_conversation_id", "chatbot_memories", ["conversation_id"], unique=False)
    op.create_index(
        "ix_chatbot_memories_user_id_status_updated_at_id",
        "chatbot_memories",
        ["user_id", "status", "updated_at", "id"],
        unique=False,
    )
    op.create_index("ix_chatbot_memories_user_id_normalized_hash", "chatbot_memories", ["user_id", "normalized_hash"], unique=False)

    op.create_table(
        "chatbot_llm_runs",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("request_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("conversation_id", sa.String(length=36), nullable=False),
        sa.Column("message_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("first_token_latency_ms", sa.Integer(), nullable=True),
        sa.Column("finish_reason", sa.String(length=50), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_chatbot_llm_runs_user_id_users", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["chatbot_conversations.id"],
            name="fk_chatbot_llm_runs_conversation_id_chatbot_conversations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["chatbot_messages.id"],
            name="fk_chatbot_llm_runs_message_id_chatbot_messages",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("message_id", name="uq_chatbot_llm_runs_message_id"),
        sa.CheckConstraint("status IN ('pending', 'streaming', 'completed', 'failed', 'cancelled')", name="ck_chatbot_llm_runs_status"),
        sa.CheckConstraint("attempt_count >= 1", name="ck_chatbot_llm_runs_attempt_count"),
        sa.CheckConstraint("prompt_tokens >= 0", name="ck_chatbot_llm_runs_prompt_tokens"),
        sa.CheckConstraint("completion_tokens >= 0", name="ck_chatbot_llm_runs_completion_tokens"),
        sa.CheckConstraint("total_tokens >= 0", name="ck_chatbot_llm_runs_total_tokens"),
    )
    op.create_index("ix_chatbot_llm_runs_request_id", "chatbot_llm_runs", ["request_id"], unique=False)
    op.create_index("ix_chatbot_llm_runs_user_id", "chatbot_llm_runs", ["user_id"], unique=False)
    op.create_index("ix_chatbot_llm_runs_conversation_id", "chatbot_llm_runs", ["conversation_id"], unique=False)
    op.create_index("ix_chatbot_llm_runs_message_id", "chatbot_llm_runs", ["message_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_chatbot_llm_runs_message_id", table_name="chatbot_llm_runs")
    op.drop_index("ix_chatbot_llm_runs_conversation_id", table_name="chatbot_llm_runs")
    op.drop_index("ix_chatbot_llm_runs_user_id", table_name="chatbot_llm_runs")
    op.drop_index("ix_chatbot_llm_runs_request_id", table_name="chatbot_llm_runs")
    op.drop_table("chatbot_llm_runs")

    op.drop_index("ix_chatbot_memories_user_id_normalized_hash", table_name="chatbot_memories")
    op.drop_index("ix_chatbot_memories_user_id_status_updated_at_id", table_name="chatbot_memories")
    op.drop_index("ix_chatbot_memories_conversation_id", table_name="chatbot_memories")
    op.drop_index("ix_chatbot_memories_user_id", table_name="chatbot_memories")
    op.drop_table("chatbot_memories")

    op.drop_index("ix_chatbot_messages_user_id_status_updated_at", table_name="chatbot_messages")
    op.drop_index("ix_chatbot_messages_conversation_id_sequence_number", table_name="chatbot_messages")
    op.drop_index("ix_chatbot_messages_parent_message_id", table_name="chatbot_messages")
    op.drop_index("ix_chatbot_messages_user_id", table_name="chatbot_messages")
    op.drop_index("ix_chatbot_messages_conversation_id", table_name="chatbot_messages")
    op.drop_table("chatbot_messages")

    op.drop_index("ix_chatbot_conversation_summaries_conversation_id", table_name="chatbot_conversation_summaries")
    op.drop_table("chatbot_conversation_summaries")

    op.drop_index("ix_chatbot_conversations_user_id_status_last_message_at_id", table_name="chatbot_conversations")
    op.drop_index("ix_chatbot_conversations_deleted_at", table_name="chatbot_conversations")
    op.drop_index("ix_chatbot_conversations_user_id", table_name="chatbot_conversations")
    op.drop_table("chatbot_conversations")
