"""create chatbot durable jobs

Revision ID: 0007_create_chatbot_jobs
Revises: 0006_create_chatbot_tables
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007_create_chatbot_jobs"
down_revision = "0006_create_chatbot_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chatbot_jobs",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("kind", sa.String(50), nullable=False),
        sa.Column("dedup_key", sa.String(255), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("dedup_key", name="uq_chatbot_jobs_dedup_key"),
        sa.CheckConstraint(
            "kind IN ('completed_turn_memory', 'refresh_conversation_context', 'auto_title', "
            "'cleanup_conversation', 'cleanup_memory')",
            name="ck_chatbot_jobs_kind",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'retry', 'completed', 'failed')",
            name="ck_chatbot_jobs_status",
        ),
        sa.CheckConstraint("attempt_count >= 0", name="ck_chatbot_jobs_attempt_count"),
    )
    op.create_index(
        "ix_chatbot_jobs_status_available_at_id",
        "chatbot_jobs",
        ["status", "available_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_chatbot_jobs_status_available_at_id", table_name="chatbot_jobs")
    op.drop_table("chatbot_jobs")
