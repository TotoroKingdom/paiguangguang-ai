"""Database-backed AgentRun state transitions.

The runtime worker uses these helpers as compare-and-swap (CAS) boundaries.  A
caller must commit the surrounding transaction; helpers flush changes so a
second operation in the same transaction observes the new state.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Iterable

from sqlalchemy import case, func, or_, select, update
from sqlalchemy.orm import Session

from app.modules.runtime.models import AgentRun

TERMINAL_STATES = frozenset({"completed", "failed", "cancelled", "timed_out"})
ACTIVE_STATES = frozenset({"queued", "running", "waiting_tool"})
_MAX_CHECKPOINT_BYTES = 2 * 1024 * 1024


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def find_idempotent_run(session: Session, *, user_id: str, idempotency_key: str) -> AgentRun | None:
    """Return the existing run for a user's non-empty idempotency key."""
    key = idempotency_key.strip()
    if not key:
        return None
    return session.scalar(
        select(AgentRun).where(
            AgentRun.user_id == user_id,
            AgentRun.idempotency_key == key,
        )
    )


def claim_run(
    session: Session,
    run_id: str,
    *,
    worker_id: str,
    now: datetime | None = None,
    lease_seconds: int = 30,
) -> bool:
    """Atomically claim a queued or expired run for one worker."""
    if not worker_id.strip() or lease_seconds <= 0:
        return False
    now = now or utc_now()
    expires = now + timedelta(seconds=lease_seconds)
    stale = or_(
        AgentRun.status == "queued",
        (AgentRun.status.in_(("running", "waiting_tool")))
        & (or_(AgentRun.lease_expires_at.is_(None), AgentRun.lease_expires_at <= now)),
    )
    result = session.execute(
        update(AgentRun)
        .where(
            AgentRun.id == run_id,
            stale,
            AgentRun.cancel_requested.is_(False),
        )
        .values(
            status="running",
            worker_id=worker_id.strip()[:128],
            heartbeat_at=now,
            lease_expires_at=expires,
            started_at=func.coalesce(AgentRun.started_at, now),
            state_version=AgentRun.state_version + 1,
            attempt=case((AgentRun.status == "queued", AgentRun.attempt), else_=AgentRun.attempt + 1),
        )
    )
    session.flush()
    return result.rowcount == 1


def heartbeat_run(
    session: Session,
    run_id: str,
    *,
    worker_id: str,
    now: datetime | None = None,
    lease_seconds: int = 30,
) -> bool:
    """Extend a worker lease only when the caller still owns the run."""
    if not worker_id.strip() or lease_seconds <= 0:
        return False
    now = now or utc_now()
    result = session.execute(
        update(AgentRun)
        .where(
            AgentRun.id == run_id,
            AgentRun.worker_id == worker_id.strip()[:128],
            AgentRun.status.in_(("running", "waiting_tool")),
            or_(AgentRun.lease_expires_at.is_(None), AgentRun.lease_expires_at > now),
        )
        .values(
            heartbeat_at=now,
            lease_expires_at=now + timedelta(seconds=lease_seconds),
            state_version=AgentRun.state_version + 1,
        )
    )
    session.flush()
    return result.rowcount == 1


def request_cancel(session: Session, run_id: str) -> bool:
    """Mark a non-terminal run for cancellation exactly once."""
    result = session.execute(
        update(AgentRun)
        .where(AgentRun.id == run_id, AgentRun.status.not_in(tuple(TERMINAL_STATES)))
        .values(cancel_requested=True, state_version=AgentRun.state_version + 1)
    )
    session.flush()
    return result.rowcount == 1


def transition_run(
    session: Session,
    run_id: str,
    *,
    from_states: Iterable[str],
    to_state: str,
    worker_id: str | None = None,
    expected_version: int | None = None,
    error_code: str = "",
    error_message: str = "",
    output_text: str | None = None,
    now: datetime | None = None,
) -> bool:
    """CAS transition with one-way terminal-state protection."""
    if to_state not in ACTIVE_STATES | TERMINAL_STATES:
        raise ValueError(f"unknown run state: {to_state}")
    allowed = tuple(state for state in dict.fromkeys(from_states) if state not in TERMINAL_STATES)
    if not allowed:
        return False
    now = now or utc_now()
    conditions = [AgentRun.id == run_id, AgentRun.status.in_(allowed)]
    if worker_id is not None:
        conditions.append(AgentRun.worker_id == worker_id)
        conditions.append(or_(AgentRun.lease_expires_at.is_(None), AgentRun.lease_expires_at > now))
    if expected_version is not None:
        conditions.append(AgentRun.state_version == expected_version)
    values: dict[str, object] = {
        "status": to_state,
        "state_version": AgentRun.state_version + 1,
    }
    if error_code:
        values["error_code"] = error_code[:64]
    if error_message:
        values["error_message"] = error_message[:500]
    if output_text is not None:
        values["output_text"] = output_text
    if to_state in TERMINAL_STATES:
        values.update({"finished_at": now, "lease_expires_at": None})
    result = session.execute(update(AgentRun).where(*conditions).values(**values))
    session.flush()
    return result.rowcount == 1


def save_checkpoint(
    session: Session,
    run_id: str,
    checkpoint: dict,
    *,
    worker_id: str | None = None,
    expected_version: int | None = None,
    status: str | None = None,
    lease_seconds: int = 30,
) -> bool:
    """Persist a bounded JSON checkpoint under the worker's CAS lease."""
    serialized = json.dumps(checkpoint, ensure_ascii=False, separators=(",", ":"))
    if len(serialized.encode("utf-8")) > _MAX_CHECKPOINT_BYTES:
        raise ValueError("checkpoint exceeds 2 MiB")
    conditions = [AgentRun.id == run_id, AgentRun.status.in_(tuple(ACTIVE_STATES))]
    if worker_id is not None:
        conditions.append(AgentRun.worker_id == worker_id)
        conditions.append(or_(AgentRun.lease_expires_at.is_(None), AgentRun.lease_expires_at > utc_now()))
    if expected_version is not None:
        conditions.append(AgentRun.state_version == expected_version)
    now = utc_now()
    values: dict[str, object] = {
        "checkpoint_json": serialized,
        "state_version": AgentRun.state_version + 1,
        "heartbeat_at": now,
        "lease_expires_at": now + timedelta(seconds=lease_seconds),
    }
    if status is not None:
        if status not in ACTIVE_STATES:
            raise ValueError("checkpoint status must be active")
        values["status"] = status
    result = session.execute(update(AgentRun).where(*conditions).values(**values))
    session.flush()
    return result.rowcount == 1


def increment_tool_count(
    session: Session,
    run_id: str,
    *,
    worker_id: str | None = None,
) -> bool:
    """Atomically reserve one tool invocation under the run's persisted quota."""
    conditions = [
        AgentRun.id == run_id,
        AgentRun.status == "running",
        AgentRun.cancel_requested.is_(False),
        AgentRun.tool_call_count < AgentRun.max_tool_calls,
        or_(AgentRun.lease_expires_at.is_(None), AgentRun.lease_expires_at > utc_now()),
    ]
    if worker_id is not None:
        conditions.append(AgentRun.worker_id == worker_id)
    result = session.execute(
        update(AgentRun)
        .where(*conditions)
        .values(tool_call_count=AgentRun.tool_call_count + 1, state_version=AgentRun.state_version + 1)
    )
    session.flush()
    return result.rowcount == 1


def is_terminal(status: str) -> bool:
    return status in TERMINAL_STATES
