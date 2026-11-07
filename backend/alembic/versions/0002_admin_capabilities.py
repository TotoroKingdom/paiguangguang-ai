"""add administrator identity and capability registry"""

from alembic import op
import sqlalchemy as sa

revision = "0002_admin_capabilities"
down_revision = "0001_assistant_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admin_users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_admin_users_username", "admin_users", ["username"], unique=True)

    op.create_table(
        "admin_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("csrf_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("client_ip", sa.String(length=64), nullable=False),
        sa.Column("user_agent", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["admin_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_admin_sessions_user_id", "admin_sessions", ["user_id"])
    op.create_index(
        "ix_admin_sessions_token_hash", "admin_sessions", ["token_hash"], unique=True
    )
    op.create_index("ix_admin_sessions_expires_at", "admin_sessions", ["expires_at"])

    op.create_table(
        "capability_definitions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("icon", sa.String(length=48), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("kind", "slug", name="uq_capability_definitions_kind_slug"),
    )
    op.create_index(
        "ix_capability_definitions_kind_status",
        "capability_definitions",
        ["kind", "status"],
    )

    op.create_table(
        "capability_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("capability_id", sa.String(length=36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("snapshot_json", sa.Text(), nullable=False),
        sa.Column("changelog", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.Column("published_by", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["capability_id"], ["capability_definitions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "capability_id", "version", name="uq_capability_versions_number"
        ),
    )
    op.create_index(
        "ix_capability_versions_capability_id",
        "capability_versions",
        ["capability_id"],
    )
    op.create_index(
        "ix_capability_versions_status",
        "capability_versions",
        ["capability_id", "status"],
    )

    op.create_table(
        "capability_dependencies",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("version_id", sa.String(length=36), nullable=False),
        sa.Column("dependency_id", sa.String(length=36), nullable=False),
        sa.Column("dependency_kind", sa.String(length=16), nullable=False),
        sa.ForeignKeyConstraint(
            ["version_id"], ["capability_versions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "version_id",
            "dependency_id",
            name="uq_capability_dependencies_version_target",
        ),
    )
    op.create_index(
        "ix_capability_dependencies_version_id",
        "capability_dependencies",
        ["version_id"],
    )

    op.create_table(
        "capability_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("capability_id", sa.String(length=36), nullable=False),
        sa.Column("version_id", sa.String(length=36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.String(length=36), nullable=False),
        sa.Column("owner_id", sa.String(length=64), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("detail_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_capability_runs_created_at", "capability_runs", ["created_at"])
    op.create_index("ix_capability_runs_capability_id", "capability_runs", ["capability_id"])
    op.create_index("ix_capability_runs_owner_id", "capability_runs", ["owner_id"])

    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("actor_type", sa.String(length=24), nullable=False),
        sa.Column("actor_id", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("resource_type", sa.String(length=48), nullable=False),
        sa.Column("resource_id", sa.String(length=64), nullable=False),
        sa.Column("detail_json", sa.Text(), nullable=False),
        sa.Column("client_ip", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])
    op.create_index("ix_audit_events_action", "audit_events", ["action"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_action", table_name="audit_events")
    op.drop_index("ix_audit_events_created_at", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ix_capability_runs_owner_id", table_name="capability_runs")
    op.drop_index("ix_capability_runs_capability_id", table_name="capability_runs")
    op.drop_index("ix_capability_runs_created_at", table_name="capability_runs")
    op.drop_table("capability_runs")
    op.drop_index("ix_capability_dependencies_version_id", table_name="capability_dependencies")
    op.drop_table("capability_dependencies")
    op.drop_index("ix_capability_versions_status", table_name="capability_versions")
    op.drop_index("ix_capability_versions_capability_id", table_name="capability_versions")
    op.drop_table("capability_versions")
    op.drop_index("ix_capability_definitions_kind_status", table_name="capability_definitions")
    op.drop_table("capability_definitions")
    op.drop_index("ix_admin_sessions_expires_at", table_name="admin_sessions")
    op.drop_index("ix_admin_sessions_token_hash", table_name="admin_sessions")
    op.drop_index("ix_admin_sessions_user_id", table_name="admin_sessions")
    op.drop_table("admin_sessions")
    op.drop_index("ix_admin_users_username", table_name="admin_users")
    op.drop_table("admin_users")
