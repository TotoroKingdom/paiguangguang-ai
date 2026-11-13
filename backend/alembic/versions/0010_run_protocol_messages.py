"""persist run protocol messages"""

from alembic import op
import sqlalchemy as sa


revision = "0010_run_protocol_messages"
down_revision = "0009_agent_dependency_versions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "run_messages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "seq", name="uq_run_messages_run_seq"),
    )
    op.create_index("ix_run_messages_run_id", "run_messages", ["run_id"])
    op.create_index("ix_run_messages_run_seq", "run_messages", ["run_id", "seq"])


def downgrade() -> None:
    op.drop_index("ix_run_messages_run_seq", table_name="run_messages")
    op.drop_index("ix_run_messages_run_id", table_name="run_messages")
    op.drop_table("run_messages")
