"""add private skills, files and MCP registry/connections"""

from alembic import op
import sqlalchemy as sa

revision = "0007_personal_resources"
down_revision = "0006_capability_governance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "personal_skills",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=False),
        sa.Column("content_md", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_personal_skills_user_id", "personal_skills", ["user_id"])
    op.create_index(
        "ix_personal_skills_user_updated", "personal_skills", ["user_id", "updated_at"]
    )

    op.create_table(
        "user_files",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("storage_path", sa.String(length=512), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_files_user_id", "user_files", ["user_id"])
    op.create_index("ix_user_files_user_created", "user_files", ["user_id", "created_at"])

    op.create_table(
        "mcp_servers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=False),
        sa.Column("endpoint_url", sa.String(length=512), nullable=False),
        sa.Column("transport", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("tools_json", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("reviewed_by", sa.String(length=36), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_mcp_servers_name"),
    )

    op.create_table(
        "mcp_connections",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("server_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("credential_ciphertext", sa.Text(), nullable=False),
        sa.Column("credential_ref", sa.String(length=160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "server_id", name="uq_mcp_connections_user_server"),
    )
    op.create_index("ix_mcp_connections_user_id", "mcp_connections", ["user_id"])
    op.create_index("ix_mcp_connections_server_id", "mcp_connections", ["server_id"])


def downgrade() -> None:
    op.drop_index("ix_mcp_connections_server_id", table_name="mcp_connections")
    op.drop_index("ix_mcp_connections_user_id", table_name="mcp_connections")
    op.drop_table("mcp_connections")
    op.drop_table("mcp_servers")
    op.drop_index("ix_user_files_user_created", table_name="user_files")
    op.drop_index("ix_user_files_user_id", table_name="user_files")
    op.drop_table("user_files")
    op.drop_index("ix_personal_skills_user_updated", table_name="personal_skills")
    op.drop_index("ix_personal_skills_user_id", table_name="personal_skills")
    op.drop_table("personal_skills")
