"""add original filename and kb state

Revision ID: 0005_add_orig_filename_kb_state
Revises: 0004_create_rag_lifecycle_tables
Create Date: 2026-07-07 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0005_add_orig_filename_kb_state"
down_revision = "0004_create_rag_lifecycle_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("rag_documents", sa.Column("original_filename", sa.String(length=255), nullable=True))
    op.create_table(
        "rag_knowledge_base_state",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("collection_name", sa.String(length=128), nullable=False),
        sa.Column("kb_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("collection_name", name="uq_rag_knowledge_base_state_collection_name"),
    )
    op.create_index(op.f("ix_rag_knowledge_base_state_collection_name"), "rag_knowledge_base_state", ["collection_name"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_rag_knowledge_base_state_collection_name"), table_name="rag_knowledge_base_state")
    op.drop_table("rag_knowledge_base_state")
    op.drop_column("rag_documents", "original_filename")
