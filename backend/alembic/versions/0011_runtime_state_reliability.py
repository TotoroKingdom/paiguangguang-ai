"""persist run leases, checkpoints, budgets and CAS state"""

from alembic import op
import sqlalchemy as sa


revision = "0011_runtime_state_reliability"
down_revision = "0010_run_protocol_messages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = [
        ("assistant_message_id", sa.String(length=36), None),
        ("client_turn_id", sa.String(length=100), None),
        ("idempotency_key", sa.String(length=160), None),
        ("attempt", sa.Integer(), 1),
        ("state_version", sa.Integer(), 0),
        ("worker_id", sa.String(length=128), None),
        ("heartbeat_at", sa.DateTime(timezone=True), None),
        ("lease_expires_at", sa.DateTime(timezone=True), None),
        ("checkpoint_json", sa.Text(), "{}"),
        ("deadline_at", sa.DateTime(timezone=True), None),
        ("max_steps", sa.Integer(), 6),
        ("max_tool_calls", sa.Integer(), 6),
        ("tool_call_count", sa.Integer(), 0),
        ("input_token_budget", sa.Integer(), 200000),
        ("output_token_budget", sa.Integer(), 100000),
    ]
    for name, type_, default in columns:
        kwargs = {"nullable": default is None}
        if default is not None:
            kwargs["server_default"] = str(default)
        op.add_column("agent_runs", sa.Column(name, type_, **kwargs))
    # Existing rows receive safe defaults, then columns remain nullable where
    # an unset value is meaningful (worker, lease, deadline, and retry key).
    op.execute("UPDATE agent_runs SET attempt = 1 WHERE attempt IS NULL")
    op.execute("UPDATE agent_runs SET state_version = 0 WHERE state_version IS NULL")
    op.execute("UPDATE agent_runs SET checkpoint_json = '{}' WHERE checkpoint_json IS NULL")
    op.execute("UPDATE agent_runs SET max_steps = 6 WHERE max_steps IS NULL")
    op.execute("UPDATE agent_runs SET max_tool_calls = 6 WHERE max_tool_calls IS NULL")
    op.execute("UPDATE agent_runs SET tool_call_count = 0 WHERE tool_call_count IS NULL")
    op.execute("UPDATE agent_runs SET input_token_budget = 200000 WHERE input_token_budget IS NULL")
    op.execute("UPDATE agent_runs SET output_token_budget = 100000 WHERE output_token_budget IS NULL")
    op.create_index("ix_agent_runs_assistant_message_id", "agent_runs", ["assistant_message_id"])
    op.create_index("ix_agent_runs_assistant_attempt", "agent_runs", ["assistant_message_id", "attempt"])
    # SQLite cannot ALTER TABLE to add constraints; a unique index provides
    # the same CAS/idempotency guarantee and permits multiple NULL keys.
    op.create_index(
        "uq_agent_runs_user_idempotency",
        "agent_runs",
        ["user_id", "idempotency_key"],
        unique=True,
    )
    with op.batch_alter_table("run_steps") as batch:
        batch.create_unique_constraint("uq_run_steps_run_seq", ["run_id", "seq"])
    with op.batch_alter_table("run_traces") as batch:
        batch.create_unique_constraint("uq_run_traces_run_seq", ["run_id", "seq"])


def downgrade() -> None:
    with op.batch_alter_table("run_traces") as batch:
        batch.drop_constraint("uq_run_traces_run_seq", type_="unique")
    with op.batch_alter_table("run_steps") as batch:
        batch.drop_constraint("uq_run_steps_run_seq", type_="unique")
    op.drop_index("uq_agent_runs_user_idempotency", table_name="agent_runs")
    op.drop_index("ix_agent_runs_assistant_attempt", table_name="agent_runs")
    op.drop_index("ix_agent_runs_assistant_message_id", table_name="agent_runs")
    for name in (
        "output_token_budget",
        "input_token_budget",
        "tool_call_count",
        "max_tool_calls",
        "max_steps",
        "deadline_at",
        "checkpoint_json",
        "lease_expires_at",
        "heartbeat_at",
        "worker_id",
        "state_version",
        "attempt",
        "idempotency_key",
        "client_turn_id",
        "assistant_message_id",
    ):
        op.drop_column("agent_runs", name)
