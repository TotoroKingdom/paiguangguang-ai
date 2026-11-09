"""add capability ownership, review, ACL and test readiness"""

from alembic import op
import sqlalchemy as sa

revision = "0006_capability_governance"
down_revision = "0005_conversation_user_ownership"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("capability_definitions", sa.Column("owner_id", sa.String(length=36)))
    op.add_column(
        "capability_definitions",
        sa.Column("visibility", sa.String(length=16), nullable=False, server_default="platform"),
    )
    op.add_column(
        "capability_definitions",
        sa.Column("access_mode", sa.String(length=16), nullable=False, server_default="all_active"),
    )
    op.add_column(
        "capability_definitions",
        sa.Column("review_status", sa.String(length=16), nullable=False, server_default="none"),
    )
    op.add_column(
        "capability_definitions",
        sa.Column("submitted_by", sa.String(length=64), nullable=False, server_default=""),
    )
    op.add_column(
        "capability_definitions", sa.Column("submitted_at", sa.DateTime(timezone=True))
    )
    op.add_column(
        "capability_definitions",
        sa.Column("reviewed_by", sa.String(length=64), nullable=False, server_default=""),
    )
    op.add_column(
        "capability_definitions", sa.Column("reviewed_at", sa.DateTime(timezone=True))
    )
    op.add_column(
        "capability_definitions",
        sa.Column("review_reason", sa.String(length=255), nullable=False, server_default=""),
    )
    op.add_column(
        "capability_definitions",
        sa.Column("test_status", sa.String(length=16), nullable=False, server_default="untested"),
    )
    op.add_column(
        "capability_definitions", sa.Column("tested_at", sa.DateTime(timezone=True))
    )
    op.add_column(
        "capability_definitions",
        sa.Column("test_detail_json", sa.Text(), nullable=False, server_default="{}"),
    )
    op.create_index(
        "ix_capability_definitions_owner_id", "capability_definitions", ["owner_id"]
    )

    op.create_table(
        "capability_grants",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("capability_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("granted_by", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["capability_id"], ["capability_definitions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "capability_id", "user_id", name="uq_capability_grants_target"
        ),
    )
    op.create_index(
        "ix_capability_grants_capability_id", "capability_grants", ["capability_id"]
    )
    op.create_index("ix_capability_grants_user_id", "capability_grants", ["user_id"])

    op.create_table(
        "capability_reviews",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("capability_id", sa.String(length=36), nullable=False),
        sa.Column("version_id", sa.String(length=36), nullable=False),
        sa.Column("action", sa.String(length=24), nullable=False),
        sa.Column("actor_id", sa.String(length=36), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_capability_reviews_capability_id", "capability_reviews", ["capability_id"])
    op.create_index(
        "ix_capability_reviews_capability",
        "capability_reviews",
        ["capability_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_capability_reviews_capability", table_name="capability_reviews")
    op.drop_index("ix_capability_reviews_capability_id", table_name="capability_reviews")
    op.drop_table("capability_reviews")
    op.drop_index("ix_capability_grants_user_id", table_name="capability_grants")
    op.drop_index("ix_capability_grants_capability_id", table_name="capability_grants")
    op.drop_table("capability_grants")
    op.drop_index("ix_capability_definitions_owner_id", table_name="capability_definitions")
    for column in (
        "test_detail_json",
        "tested_at",
        "test_status",
        "review_reason",
        "reviewed_at",
        "reviewed_by",
        "submitted_at",
        "submitted_by",
        "review_status",
        "access_mode",
        "visibility",
        "owner_id",
    ):
        op.drop_column("capability_definitions", column)
