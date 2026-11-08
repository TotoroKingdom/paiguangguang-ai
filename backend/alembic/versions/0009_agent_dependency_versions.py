"""lock agent dependency versions"""

from alembic import op
import sqlalchemy as sa

revision = "0009_agent_dependency_versions"
down_revision = "0008_runtime_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "capability_dependencies",
        sa.Column(
            "dependency_version_id",
            sa.String(length=36),
            nullable=False,
            server_default="",
        ),
    )


def downgrade() -> None:
    op.drop_column("capability_dependencies", "dependency_version_id")
