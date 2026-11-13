from datetime import datetime, timedelta

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import Base
from app.modules.runtime.models import AgentRun
from app.modules.runtime.state import (
    TERMINAL_STATES,
    claim_run,
    find_idempotent_run,
    heartbeat_run,
    increment_tool_count,
    is_terminal,
    request_cancel,
    save_checkpoint,
    transition_run,
)


def _session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return Session(engine)


def _run(session, **kwargs):
    run = AgentRun(
        user_id="user-1",
        created_at=datetime.utcnow(),
        status="queued",
        max_tool_calls=2,
        idempotency_key=kwargs.pop("idempotency_key", None),
        **kwargs,
    )
    session.add(run)
    session.commit()
    return run


def test_claim_fences_competing_workers_and_heartbeat_extends_lease():
    with _session() as session:
        run = _run(session)
        assert claim_run(session, run.id, worker_id="worker-a", lease_seconds=20)
        session.commit()
        assert not claim_run(session, run.id, worker_id="worker-b", lease_seconds=20)
        assert heartbeat_run(session, run.id, worker_id="worker-a", lease_seconds=30)
        session.refresh(run)
        assert run.worker_id == "worker-a"
        assert run.lease_expires_at is not None


def test_expired_lease_can_be_reclaimed_and_attempt_increments():
    with _session() as session:
        run = _run(session)
        assert claim_run(session, run.id, worker_id="worker-a", lease_seconds=1)
        session.commit()
        old = datetime.utcnow() - timedelta(minutes=1)
        run.lease_expires_at = old
        session.commit()
        assert claim_run(session, run.id, worker_id="worker-b", now=datetime.utcnow(), lease_seconds=20)
        session.refresh(run)
        assert run.worker_id == "worker-b"
        assert run.attempt == 2


def test_waiting_tool_requires_expired_lease_before_reclaim():
    with _session() as session:
        run = _run(session)
        assert claim_run(session, run.id, worker_id="worker-a", lease_seconds=30)
        session.commit()
        assert transition_run(
            session,
            run.id,
            from_states=("running",),
            to_state="waiting_tool",
            worker_id="worker-a",
        )
        session.commit()
        assert not claim_run(session, run.id, worker_id="worker-b", lease_seconds=30)
        run.lease_expires_at = datetime.utcnow() - timedelta(minutes=1)
        session.commit()
        assert claim_run(session, run.id, worker_id="worker-b", lease_seconds=30)


def test_terminal_transition_is_single_winner_and_cancel_blocks_tool_claim():
    with _session() as session:
        run = _run(session)
        assert claim_run(session, run.id, worker_id="worker-a")
        session.commit()
        assert request_cancel(session, run.id)
        session.commit()
        assert not increment_tool_count(session, run.id, worker_id="worker-a")
        assert transition_run(
            session,
            run.id,
            from_states=("running",),
            to_state="cancelled",
            worker_id="worker-a",
        )
        session.commit()
        assert not transition_run(
            session,
            run.id,
            from_states=("cancelled",),
            to_state="completed",
            worker_id="worker-a",
        )
        assert is_terminal("cancelled")
        assert TERMINAL_STATES == {"completed", "failed", "cancelled", "timed_out"}


def test_cancelled_run_cannot_complete_and_graph_rejects_invalid_edges():
    with _session() as session:
        run = _run(session)
        assert not transition_run(
            session, run.id, from_states=("queued",), to_state="completed"
        )
        assert claim_run(session, run.id, worker_id="worker-a")
        session.commit()
        assert request_cancel(session, run.id)
        session.commit()
        assert not transition_run(
            session,
            run.id,
            from_states=("running",),
            to_state="completed",
            worker_id="worker-a",
        )


def test_worker_writes_require_non_expired_non_null_lease():
    with _session() as session:
        run = _run(session)
        assert claim_run(session, run.id, worker_id="worker-a")
        session.commit()
        run.lease_expires_at = None
        session.commit()
        assert not heartbeat_run(session, run.id, worker_id="worker-a")
        assert not save_checkpoint(session, run.id, {"next": 1}, worker_id="worker-a")
        assert not increment_tool_count(session, run.id, worker_id="worker-a")
        assert not transition_run(
            session, run.id, from_states=("running",), to_state="completed", worker_id="worker-a"
        )


def test_checkpoint_and_tool_quota_are_bounded_and_idempotent_lookup_is_scoped():
    with _session() as session:
        run = _run(session, idempotency_key="turn-1")
        assert find_idempotent_run(session, user_id="user-1", idempotency_key="turn-1").id == run.id
        assert find_idempotent_run(session, user_id="user-2", idempotency_key="turn-1") is None
        assert claim_run(session, run.id, worker_id="worker-a")
        assert save_checkpoint(
            session,
            run.id,
            {"messages": [{"role": "assistant", "tool_calls": []}], "next": 2},
            worker_id="worker-a",
        )
        assert increment_tool_count(session, run.id, worker_id="worker-a")
        assert increment_tool_count(session, run.id, worker_id="worker-a")
        assert not increment_tool_count(session, run.id, worker_id="worker-a")
        session.commit()
        stored = session.scalar(select(AgentRun).where(AgentRun.id == run.id))
        assert stored.tool_call_count == 2
        assert '"next":2' in stored.checkpoint_json
