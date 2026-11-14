"""add nullable conversation user ownership for explicit legacy claiming"""

from alembic import op
import sqlalchemy as sa

revision = "0005_conversation_user_ownership"
down_revision = "0004_identity_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "conversations", sa.Column("user_id", sa.String(length=36), nullable=True)
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_conversations_user_id", table_name="conversations")
    op.drop_column("conversations", "user_id")
