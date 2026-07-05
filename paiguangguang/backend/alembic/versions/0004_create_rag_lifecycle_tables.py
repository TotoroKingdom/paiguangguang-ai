"""create rag lifecycle tables

Revision ID: 0004_create_rag_lifecycle_tables
Revises: 0003_create_rbac_tables
Create Date: 2026-07-05 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0004_create_rag_lifecycle_tables"
down_revision = "0003_create_rbac_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rag_documents",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("document_id", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("owner_user_id", sa.String(length=36), nullable=True),
        sa.Column("workspace_id", sa.String(length=36), nullable=True),
        sa.Column("permission_scope", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default=sa.text("'registered'")),
        sa.Column("parse_status", sa.String(length=50), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("chunk_status", sa.String(length=50), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("embedding_status", sa.String(length=50), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("index_status", sa.String(length=50), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("document_id", name="uq_rag_documents_document_id"),
    )
    op.create_index(op.f("ix_rag_documents_document_id"), "rag_documents", ["document_id"], unique=False)
    op.create_index(op.f("ix_rag_documents_content_hash"), "rag_documents", ["content_hash"], unique=False)
    op.create_table(
        "rag_chunks",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("chunk_id", sa.String(length=128), nullable=False),
        sa.Column("document_id", sa.String(length=128), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("start_char", sa.Integer(), nullable=False),
        sa.Column("end_char", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("chunk_id", name="uq_rag_chunks_chunk_id"),
    )
    op.create_index(op.f("ix_rag_chunks_chunk_id"), "rag_chunks", ["chunk_id"], unique=False)
    op.create_index(op.f("ix_rag_chunks_document_id"), "rag_chunks", ["document_id"], unique=False)
    op.create_table(
        "rag_ingestion_jobs",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("job_id", sa.String(length=128), nullable=False),
        sa.Column("document_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_reindex", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("chunk_size", sa.Integer(), nullable=True),
        sa.Column("chunk_overlap", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("job_id", name="uq_rag_ingestion_jobs_job_id"),
    )
    op.create_index(op.f("ix_rag_ingestion_jobs_job_id"), "rag_ingestion_jobs", ["job_id"], unique=False)
    op.create_index(op.f("ix_rag_ingestion_jobs_document_id"), "rag_ingestion_jobs", ["document_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_rag_ingestion_jobs_document_id"), table_name="rag_ingestion_jobs")
    op.drop_index(op.f("ix_rag_ingestion_jobs_job_id"), table_name="rag_ingestion_jobs")
    op.drop_table("rag_ingestion_jobs")
    op.drop_index(op.f("ix_rag_chunks_document_id"), table_name="rag_chunks")
    op.drop_index(op.f("ix_rag_chunks_chunk_id"), table_name="rag_chunks")
    op.drop_table("rag_chunks")
    op.drop_index(op.f("ix_rag_documents_content_hash"), table_name="rag_documents")
    op.drop_index(op.f("ix_rag_documents_document_id"), table_name="rag_documents")
    op.drop_table("rag_documents")
