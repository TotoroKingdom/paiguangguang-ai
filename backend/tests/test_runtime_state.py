from datetime import timedelta

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import Base
from app.modules.runtime.models import AgentRun, RunSlot
from app.modules.runtime.state import (
    TERMINAL_STATES,
    acquire_user_slot,
    claim_run,
    find_idempotent_run,
    heartbeat_run,
    increment_tool_count,
    is_terminal,
    request_cancel,
    save_checkpoint,
    transition_run,
    utc_now,
)


def _session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return Session(engine)


def _run(session, **kwargs):
    run = AgentRun(
        user_id=kwargs.pop("user_id", "user-1"),
        created_at=utc_now(),
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
        old = utc_now() - timedelta(minutes=1)
        run.lease_expires_at = old
        session.commit()
        assert claim_run(session, run.id, worker_id="worker-b", now=utc_now(), lease_seconds=20)
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
        run.lease_expires_at = utc_now() - timedelta(minutes=1)
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


def test_user_concurrency_slot_is_scoped_and_released_on_terminal_state():
    with _session() as session:
        first = _run(session, user_id="user-1")
        second = _run(session, user_id="user-1")
        other_user = _run(session, user_id="user-2")
        assert acquire_user_slot(
            session,
            user_id="user-1",
            run_id=first.id,
        )
        assert not acquire_user_slot(
            session,
            user_id="user-1",
            run_id=second.id,
        )
        assert acquire_user_slot(
            session,
            user_id="user-2",
            run_id=other_user.id,
        )
        assert transition_run(
            session,
            first.id,
            from_states=("queued",),
            to_state="cancelled",
        )
        session.commit()
        assert session.get(RunSlot, "user-1") is None
        assert acquire_user_slot(
            session,
            user_id="user-1",
            run_id=second.id,
        )
