"""add per-user runtime concurrency slots"""

from alembic import op
import sqlalchemy as sa


revision = "0012_runtime_user_slots"
down_revision = "0011_runtime_state_reliability"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "run_slots",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("user_id"),
        sa.UniqueConstraint("run_id"),
    )


def downgrade() -> None:
    op.drop_table("run_slots")
