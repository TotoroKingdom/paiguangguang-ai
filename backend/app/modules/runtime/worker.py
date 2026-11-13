"""Process-local run worker used to decouple SSE delivery from execution.

The worker owns its SQLAlchemy Session and keeps no request-bound objects. A
lease is claimed in the database before execution; this prevents a reconnect
or a second request from starting the same Run concurrently. A process crash
still requires a later lease sweep, so this module does not claim durable
queue semantics by itself.
"""

import asyncio
import inspect
import json
import uuid
from types import SimpleNamespace
from typing import Any

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Message
from app.modules.identity.models import User
from app.modules.identity.user_service import UserPrincipal
from app.modules.runtime.models import AgentRun, RunMessage, RunStep
from app.modules.runtime.service import RuntimeService
from app.modules.runtime.state import (
    claim_run as claim_state_run,
    heartbeat_run as heartbeat_state_run,
    save_checkpoint,
    transition_run,
)
from app.repositories import OwnerScope, utc_now
from app.schemas import CapabilityRef, MessageRequest, TurnCreate


_tasks: dict[str, asyncio.Task[Any]] = {}
_LEASE_SECONDS = 30
_HEARTBEAT_INTERVAL = 5.0


def _retain(run_id: str, task: asyncio.Task[Any]) -> None:
    _tasks[run_id] = task
    task.add_done_callback(
        lambda completed: _on_task_done(run_id, completed)
    )


def _on_task_done(run_id: str, task: asyncio.Task[Any]) -> None:
    _tasks.pop(run_id, None)
    if task.cancelled():
        return
    error = task.exception()
    if error is None:
        return
    with SessionLocal() as session:
        transition_run(
            session,
            run_id,
            from_states=("queued", "running", "waiting_tool"),
            to_state="failed",
            error_code="RUN_WORKER_ERROR",
            error_message=str(error)[:500],
        )
        run = session.get(AgentRun, run_id)
        if run is not None and run.assistant_message_id:
            assistant = session.get(Message, run.assistant_message_id)
            if assistant is not None and assistant.status == "generating":
                assistant.status = "error"
                assistant.content = "执行失败：运行时内部错误"
                assistant.updated_at = utc_now()
        session.commit()


def claim_run(run_id: str, worker_id: str) -> bool:
    """Claim one queued/expired run using a single conditional UPDATE."""
    now = utc_now()
    lease_until = now.replace(microsecond=now.microsecond)  # preserve timezone value
    from datetime import timedelta

    lease_until += timedelta(seconds=_LEASE_SECONDS)
    with SessionLocal() as session:
        result = claim_state_run(session, run_id, worker_id=worker_id, now=now, lease_seconds=_LEASE_SECONDS)
        session.commit()
        return result


async def execute_run_job(
    run_id: str,
    *,
    user_id: str | None = None,
    assistant_message_id: str | None = None,
    payload: TurnCreate | dict[str, Any] | None = None,
) -> None:
    worker_id = f"worker:{uuid.uuid4().hex}"
    if not claim_run(run_id, worker_id):
        _finalize_unclaimed_cancel(run_id)
        return
    with SessionLocal() as session:
        run = session.get(AgentRun, run_id)
        if run is None:
            return
        user_id = user_id or run.user_id
        user = session.get(User, user_id)
        assistant_message_id = assistant_message_id or run.assistant_message_id
        assistant = (
            session.get(Message, assistant_message_id)
            if assistant_message_id
            else None
        )
        if assistant is None:
            assistant = session.scalar(
                select(Message)
                .where(
                    Message.conversation_id == run.conversation_id,
                    Message.role == "assistant",
                    Message.client_turn_id == run.client_turn_id,
                )
                .order_by(Message.seq.desc())
            )
        if user is None or assistant is None:
            return
        turn = _turn_from_payload_or_messages(
            session,
            run=run,
            assistant=assistant,
            payload=payload,
        )
        principal = UserPrincipal(user=user, session=SimpleNamespace(scope="FULL"))
        scope = OwnerScope(owner_id="", user_id=user_id)
        service = RuntimeService(session)
        checkpoint = _safe_checkpoint(run.checkpoint_json)
        stream_kwargs: dict[str, Any] = {
            "run": run,
            "principal": principal,
            "scope": scope,
            "assistant_message_id": assistant.id,
            "payload": turn,
        }
        parameters = inspect.signature(service.stream).parameters
        if "worker_id" in parameters:
            stream_kwargs["worker_id"] = worker_id
        if "resume_checkpoint" in parameters:
            stream_kwargs["resume_checkpoint"] = checkpoint
        heartbeat_task = asyncio.create_task(
            _heartbeat_loop(run_id, worker_id),
            name=f"heartbeat:{run_id}",
        )
        try:
            async for _event in service.stream(**stream_kwargs):
                latest_message = int(
                    session.scalar(
                        select(RunMessage.seq)
                        .where(RunMessage.run_id == run_id)
                        .order_by(RunMessage.seq.desc())
                        .limit(1)
                    )
                    or 0
                )
                latest_step = int(
                    session.scalar(
                        select(RunStep.seq)
                        .where(RunStep.run_id == run_id)
                        .order_by(RunStep.seq.desc())
                        .limit(1)
                    )
                    or 0
                )
                save_checkpoint(
                    session,
                    run_id,
                    {
                        "protocolMessageSeq": latest_message,
                        "stepSeq": latest_step,
                    },
                    worker_id=worker_id,
                    lease_seconds=_LEASE_SECONDS,
                )
                session.commit()
        finally:
            heartbeat_task.cancel()
            await asyncio.gather(heartbeat_task, return_exceptions=True)
            session.expire_all()


def _safe_checkpoint(value: str | None) -> dict[str, Any]:
    try:
        parsed = json.loads(value or "{}")
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _finalize_unclaimed_cancel(run_id: str) -> None:
    with SessionLocal() as session:
        run = session.get(AgentRun, run_id)
        if run is None or not run.cancel_requested:
            return
        transition_run(
            session,
            run_id,
            from_states=("queued",),
            to_state="cancelled",
        )
        if run.assistant_message_id:
            assistant = session.get(Message, run.assistant_message_id)
            if assistant is not None and assistant.status == "generating":
                assistant.status = "stopped"
                assistant.updated_at = utc_now()
        session.commit()


def _turn_from_payload_or_messages(
    session,
    *,
    run: AgentRun,
    assistant: Message,
    payload: TurnCreate | dict[str, Any] | None,
) -> TurnCreate:
    if isinstance(payload, TurnCreate):
        return payload
    if isinstance(payload, dict) and payload:
        return TurnCreate.model_validate(payload)
    request_data = json.loads(assistant.request_json or "{}")
    request = MessageRequest.model_validate(request_data)
    user_message = session.scalar(
        select(Message).where(
            Message.conversation_id == run.conversation_id,
            Message.seq == assistant.seq - 1,
            Message.role == "user",
        )
    )
    capability_data = (
        json.loads(user_message.capability_json or "null")
        if user_message is not None
        else None
    )
    capability = (
        CapabilityRef.model_validate(capability_data)
        if isinstance(capability_data, dict)
        else None
    )
    return TurnCreate(
        clientTurnId=run.client_turn_id or request.clientTurnId,
        text=run.input_text,
        capability=capability,
        attachments=[],
        request=request.model_copy(
            update={
                "conversationId": run.conversation_id,
                "clientTurnId": run.client_turn_id or request.clientTurnId,
                "text": run.input_text,
                "capability": capability,
            }
        ),
    )


async def _heartbeat_loop(run_id: str, worker_id: str) -> None:
    while True:
        await asyncio.sleep(_HEARTBEAT_INTERVAL)
        if not heartbeat_run(run_id, worker_id):
            return


def heartbeat_run(run_id: str, worker_id: str) -> bool:
    """Extend a worker lease without holding the Runtime session transaction."""
    now = utc_now()
    from datetime import timedelta

    with SessionLocal() as session:
        result = heartbeat_state_run(session, run_id, worker_id=worker_id, now=now, lease_seconds=_LEASE_SECONDS)
        session.commit()
        return result


def start_run_job(
    run_id: str,
    *,
    user_id: str | None = None,
    assistant_message_id: str | None = None,
    payload: TurnCreate | dict[str, Any] | None = None,
) -> asyncio.Task[Any]:
    existing = _tasks.get(run_id)
    if existing is not None and not existing.done():
        return existing
    task = asyncio.create_task(
        execute_run_job(
            run_id,
            user_id=user_id,
            assistant_message_id=assistant_message_id,
            payload=payload,
        )
    )
    _retain(run_id, task)
    return task


async def recover_expired_runs() -> int:
    """Requeue runs whose worker lease was lost during a process restart."""
    now = utc_now()
    with SessionLocal() as session:
        run_ids = list(
            session.scalars(
                select(AgentRun.id)
                .where(
                    AgentRun.status.in_(("queued", "running", "waiting_tool")),
                    (AgentRun.status == "queued")
                    | AgentRun.lease_expires_at.is_(None)
                    | (AgentRun.lease_expires_at <= now),
                )
                .order_by(AgentRun.created_at)
                .limit(100)
            )
        )
    for run_id in run_ids:
        start_run_job(run_id)
    return len(run_ids)

