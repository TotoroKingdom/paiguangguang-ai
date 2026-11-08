"""add unified sessions, recovery codes, admin links and auth rate events"""

from alembic import op
import sqlalchemy as sa

revision = "0004_identity_sessions"
down_revision = "0003_identity_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("csrf_hash", sa.String(length=64), nullable=False),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("authz_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("client_ip", sa.String(length=64), nullable=False),
        sa.Column("user_agent", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index(
        "ix_user_sessions_token_hash", "user_sessions", ["token_hash"], unique=True
    )
    op.create_index("ix_user_sessions_expires_at", "user_sessions", ["expires_at"])

    op.create_table(
        "user_recovery_codes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_recovery_codes_user_id", "user_recovery_codes", ["user_id"])
    op.create_index(
        "ix_user_recovery_codes_user",
        "user_recovery_codes",
        ["user_id", "used_at"],
    )

    op.create_table(
        "admin_user_links",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("legacy_admin_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("migrated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("migration_source", sa.String(length=48), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("legacy_admin_id", name="uq_admin_user_links_legacy"),
        sa.UniqueConstraint("user_id", name="uq_admin_user_links_user"),
    )

    op.create_table(
        "auth_rate_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("bucket", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_auth_rate_events_bucket",
        "auth_rate_events",
        ["action", "bucket", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_auth_rate_events_bucket", table_name="auth_rate_events")
    op.drop_table("auth_rate_events")
    op.drop_table("admin_user_links")
    op.drop_index("ix_user_recovery_codes_user", table_name="user_recovery_codes")
    op.drop_index("ix_user_recovery_codes_user_id", table_name="user_recovery_codes")
    op.drop_table("user_recovery_codes")
    op.drop_index("ix_user_sessions_expires_at", table_name="user_sessions")
    op.drop_index("ix_user_sessions_token_hash", table_name="user_sessions")
    op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
    op.drop_table("user_sessions")
