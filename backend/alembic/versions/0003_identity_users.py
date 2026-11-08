"""add unified users, account sequence and registration idempotency"""

from alembic import op
import sqlalchemy as sa

revision = "0003_identity_users"
down_revision = "0002_admin_capabilities"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("account_number", sa.String(length=32), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("nickname", sa.String(length=80), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("status_reason", sa.String(length=255), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("authz_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_number", name="uq_users_account_number"),
    )
    op.create_index("ix_users_status_role", "users", ["status", "role"])

    op.create_table(
        "account_sequences",
        sa.Column("name", sa.String(length=32), nullable=False),
        sa.Column("next_account_number", sa.String(length=32), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("name"),
    )

    op.create_table(
        "registration_idempotency",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("response_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash"),
    )
    op.create_index(
        "ix_registration_idempotency_created_at",
        "registration_idempotency",
        ["created_at"],
    )

    op.execute(
        sa.text(
            "INSERT INTO account_sequences (name, next_account_number, updated_at) "
            "VALUES ('user_account', '100', CURRENT_TIMESTAMP)"
        )
    )


def downgrade() -> None:
    op.drop_index(
        "ix_registration_idempotency_created_at",
        table_name="registration_idempotency",
    )
    op.drop_table("registration_idempotency")
    op.drop_table("account_sequences")
    op.drop_index("ix_users_status_role", table_name="users")
    op.drop_table("users")
