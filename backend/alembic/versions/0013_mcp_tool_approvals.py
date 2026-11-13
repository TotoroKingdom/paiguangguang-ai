"""persist administrator approval for individual MCP tools"""

from datetime import datetime, timezone
import hashlib
import json
import uuid

from alembic import op
import sqlalchemy as sa


revision = "0013_mcp_tool_approvals"
down_revision = "0012_runtime_user_slots"
branch_labels = None
depends_on = None


def _fingerprint(name: str, description: str, input_schema: dict, output_schema):
    value = {
        "name": name,
        "description": description,
        "inputSchema": input_schema,
        "outputSchema": output_schema,
    }
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def upgrade() -> None:
    op.add_column(
        "mcp_servers",
        sa.Column("tool_revision", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "mcp_server_tools",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("server_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=False, server_default=""),
        sa.Column("input_schema_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("output_schema_json", sa.Text(), nullable=False, server_default="null"),
        sa.Column("schema_fingerprint", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("approval_status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("risk_class", sa.String(length=32), nullable=False, server_default="unknown"),
        sa.Column("approval_reason", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("approved_by", sa.String(length=36), nullable=False, server_default=""),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["server_id"], ["mcp_servers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("server_id", "name", name="uq_mcp_server_tools_server_name"),
    )
    op.create_index(
        "ix_mcp_server_tools_server_id", "mcp_server_tools", ["server_id"], unique=False
    )
    op.create_index(
        "ix_mcp_server_tools_server_status",
        "mcp_server_tools",
        ["server_id", "approval_status"],
        unique=False,
    )

    # Existing snapshots are deliberately imported as pending/unknown. No
    # external readOnlyHint or legacy snapshot is sufficient for approval.
    bind = op.get_bind()
    servers = sa.Table(
        "mcp_servers",
        sa.MetaData(),
        sa.Column("id", sa.String(length=36)),
        sa.Column("tools_json", sa.Text()),
    )
    tools = sa.Table(
        "mcp_server_tools",
        sa.MetaData(),
        *[
            sa.Column(name, column.type)
            for name, column in [
                ("id", sa.Column("id", sa.String(length=36))),
                ("server_id", sa.Column("server_id", sa.String(length=36))),
                ("name", sa.Column("name", sa.String(length=200))),
                ("description", sa.Column("description", sa.String(length=2000))),
                ("input_schema_json", sa.Column("input_schema_json", sa.Text())),
                ("output_schema_json", sa.Column("output_schema_json", sa.Text())),
                ("schema_fingerprint", sa.Column("schema_fingerprint", sa.String(length=64))),
                ("approval_status", sa.Column("approval_status", sa.String(length=16))),
                ("risk_class", sa.Column("risk_class", sa.String(length=32))),
                ("approval_reason", sa.Column("approval_reason", sa.String(length=255))),
                ("approved_by", sa.Column("approved_by", sa.String(length=36))),
                ("approved_at", sa.Column("approved_at", sa.DateTime(timezone=True))),
                ("discovered_at", sa.Column("discovered_at", sa.DateTime(timezone=True))),
                ("updated_at", sa.Column("updated_at", sa.DateTime(timezone=True))),
            ]
        ],
    )
    now = datetime.now(timezone.utc)
    for server_id, raw_tools in bind.execute(sa.select(servers.c.id, servers.c.tools_json)):
        try:
            entries = json.loads(raw_tools or "[]")
        except (TypeError, ValueError):
            entries = []
        if not isinstance(entries, list):
            continue
        seen = set()
        for item in entries:
            if not isinstance(item, dict) or not isinstance(item.get("name"), str):
                continue
            name = item["name"].strip()
            if not name or name in seen:
                continue
            seen.add(name)
            description = str(item.get("description", ""))[:2000]
            input_schema = item.get("inputSchema")
            if not isinstance(input_schema, dict):
                input_schema = {}
            output_schema = item.get("outputSchema")
            if output_schema is not None and not isinstance(output_schema, dict):
                output_schema = None
            bind.execute(
                tools.insert().values(
                    id=str(uuid.uuid4()),
                    server_id=server_id,
                    name=name,
                    description=description,
                    input_schema_json=json.dumps(input_schema, ensure_ascii=False, separators=(",", ":")),
                    output_schema_json=json.dumps(output_schema, ensure_ascii=False, separators=(",", ":")),
                    schema_fingerprint=_fingerprint(name, description, input_schema, output_schema),
                    approval_status="pending",
                    risk_class="unknown",
                    approval_reason="旧快照需要管理员重新批准",
                    approved_by="",
                    approved_at=None,
                    discovered_at=now,
                    updated_at=now,
                )
            )
    # Legacy snapshots are not an authorization source. The imported rows above
    # start pending, so the compatibility cache must remain empty until approval.
    bind.execute(sa.update(servers).values(tools_json="[]"))


def downgrade() -> None:
    op.drop_index("ix_mcp_server_tools_server_status", table_name="mcp_server_tools")
    op.drop_index("ix_mcp_server_tools_server_id", table_name="mcp_server_tools")
    op.drop_table("mcp_server_tools")
    op.drop_column("mcp_servers", "tool_revision")
