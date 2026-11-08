import json
from datetime import timedelta
from datetime import timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.db import get_db
from app.modules.capabilities.service import CapabilityService
from app.modules.identity.dependencies import (
    require_active_user,
    require_unified_admin,
    require_user_csrf,
)
from app.modules.identity.user_service import UserPrincipal
from app.modules.runtime.models import AgentRun
from app.modules.runtime.schemas import (
    CancelResponse,
    ExecuteRequest,
    RunListResponse,
    RunView,
    RunQuotaResponse,
)
from app.modules.runtime.service import RuntimeService, run_view
from app.modules.personal.models import PersonalSkill
from app.core.errors import APIError
from app.owner import require_json_request
from app.repositories import utc_now
from app.repositories import OwnerScope
from app.schemas import CapabilityRef, MessageRequest, TurnCreate
from app.services import ConversationService, message_response

router = APIRouter(prefix="/assistant", tags=["assistant-runtime"])
admin_router = APIRouter(prefix="/admin/assistant", tags=["admin-runtime"])


def _turn_payload(
    payload: ExecuteRequest, session: Session, user_id: str
) -> tuple[TurnCreate, str, str]:
    capability = None
    version_id = ""
    capability_id = ""
    if payload.capabilityId:
        try:
            definition, version, public = CapabilityService(session).resolve_published(
                payload.capabilityId, payload.capabilityKind
            )
            capability = CapabilityRef(id=definition.id, kind=definition.kind, name=public.name)
            capability_id = definition.id
            version_id = version.id
        except APIError:
            raise
        except Exception as error:
            if payload.capabilityKind != "skill":
                raise
            personal = session.scalar(
                select(PersonalSkill).where(
                    PersonalSkill.id == payload.capabilityId,
                    PersonalSkill.user_id == user_id,
                )
            )
            if personal is None:
                raise APIError(404, "NOT_FOUND", "个人技能不存在") from error
            capability = CapabilityRef(id=personal.id, kind="skill", name=personal.name)
            capability_id = personal.id
    turn = TurnCreate(
        clientTurnId=payload.clientTurnId,
        text=payload.text,
        capability=capability,
        attachments=[],
        request=MessageRequest(
            conversationId=payload.conversationId,
            clientTurnId=payload.clientTurnId,
            text=payload.text,
            capability=capability,
        ),
    )
    return turn, capability_id, version_id


def _load_run(session: Session, run_id: str) -> AgentRun:
    session.expire_all()
    run = session.scalar(
        select(AgentRun)
        .where(AgentRun.id == run_id)
        .options(selectinload(AgentRun.steps), selectinload(AgentRun.traces))
    )
    return run


async def _stream_events(
    session: Session,
    principal: UserPrincipal,
    scope: OwnerScope,
    turn: TurnCreate,
    capability_id: str,
    version_id: str,
    mode: str,
    assistant_id: str,
):
    service = RuntimeService(session)
    run = service.create_run(
        principal,
        conversation_id=turn.request.conversationId or "",
        version_id=version_id,
        capability_id=capability_id,
        input_text=turn.text,
        mode=mode,
    )
    async for event in service.stream(
        run,
        principal=principal,
        scope=scope,
        assistant_message_id=assistant_id,
        payload=turn,
    ):
        yield event


@router.post("/runs")
async def execute_run(
    payload: ExecuteRequest,
    request: Request,
    principal: UserPrincipal = Depends(require_active_user),
    session: Session = Depends(get_db),
):
    require_json_request(request)
    require_user_csrf(request, principal)
    scope = OwnerScope(owner_id="", user_id=principal.user.id)
    turn, capability_id, version_id = _turn_payload(payload, session, principal.user.id)
    turn_result = ConversationService(session).create_turn(
        scope, payload.conversationId, turn
    )
    run_id = ""
    async for event in _stream_events(
        session,
        principal,
        scope,
        turn,
        capability_id,
        version_id,
        payload.mode,
        turn_result.assistantMessage.id,
    ):
        if event.get("runId"):
            run_id = event["runId"]
        if event["type"] == "done" and run_id:
            break
    run = _load_run(session, run_id)
    return {
        "run": run_view(run) if run else None,
        "userMessage": turn_result.userMessage,
        "assistantMessage": turn_result.assistantMessage,
    }


@router.post("/runs/stream")
async def stream_run(
    payload: ExecuteRequest,
    request: Request,
    principal: UserPrincipal = Depends(require_active_user),
    session: Session = Depends(get_db),
):
    require_json_request(request)
    require_user_csrf(request, principal)
    scope = OwnerScope(owner_id="", user_id=principal.user.id)
    turn, capability_id, version_id = _turn_payload(payload, session, principal.user.id)
    turn_result = ConversationService(session).create_turn(
        scope, payload.conversationId, turn
    )

    async def events():
        try:
            yield (
                "data: "
                + json.dumps(
                    {
                        "type": "start",
                        "conversation": turn_result.conversation.model_dump(mode="json"),
                        "userMessage": turn_result.userMessage.model_dump(mode="json"),
                        "assistantMessage": turn_result.assistantMessage.model_dump(mode="json"),
                    },
                    ensure_ascii=False,
                )
                + "\n\n"
            )
            async for event in _stream_events(
                session,
                principal,
                scope,
                turn,
                capability_id,
                version_id,
                payload.mode,
                turn_result.assistantMessage.id,
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as error:
            yield (
                "data: "
                + json.dumps(
                    {
                        "type": "error",
                        "code": getattr(error, "code", "RUN_START_FAILED"),
                        "message": str(error),
                    },
                    ensure_ascii=False,
                )
                + "\n\n"
            )

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/runs", response_model=RunListResponse)
def list_my_runs(
    principal: UserPrincipal = Depends(require_active_user),
    session: Session = Depends(get_db),
):
    runs = list(
        session.scalars(
            select(AgentRun)
            .where(AgentRun.user_id == principal.user.id)
            .options(selectinload(AgentRun.steps), selectinload(AgentRun.traces))
            .order_by(AgentRun.created_at.desc())
            .limit(50)
        )
    )
    return RunListResponse(items=[RunView.model_validate(run_view(run)) for run in runs])


@router.get("/runs/quota", response_model=RunQuotaResponse)
def my_run_quota(
    principal: UserPrincipal = Depends(require_active_user),
    session: Session = Depends(get_db),
):
    now = utc_now()
    since = now.replace(hour=0, minute=0, second=0, microsecond=0)
    used = int(
        session.scalar(
            select(func.count(AgentRun.id)).where(
                AgentRun.user_id == principal.user.id,
                AgentRun.created_at >= since,
            )
        )
        or 0
    )
    limit = settings.llm_daily_request_limit
    return RunQuotaResponse(
        limit=limit,
        used=used,
        remaining=max(limit - used, 0),
        resetsAt=(since + timedelta(days=1)).isoformat() + "Z",
    )


@router.get("/runs/{run_id}", response_model=RunView)
def get_my_run(
    run_id: str,
    principal: UserPrincipal = Depends(require_active_user),
    session: Session = Depends(get_db),
):
    run = session.scalar(
        select(AgentRun)
        .where(AgentRun.id == run_id, AgentRun.user_id == principal.user.id)
        .options(selectinload(AgentRun.steps), selectinload(AgentRun.traces))
    )
    if run is None:
        from app.core.errors import APIError

        raise APIError(404, "NOT_FOUND", "Run 不存在")
    return RunView.model_validate(run_view(run))


@router.post("/runs/{run_id}/cancel", response_model=CancelResponse)
def cancel_run(
    run_id: str,
    request: Request,
    principal: UserPrincipal = Depends(require_active_user),
    session: Session = Depends(get_db),
):
    require_json_request(request)
    require_user_csrf(request, principal)
    run = session.scalar(
        select(AgentRun).where(AgentRun.id == run_id, AgentRun.user_id == principal.user.id)
    )
    if run is None:
        from app.core.errors import APIError

        raise APIError(404, "NOT_FOUND", "Run 不存在")
    if run.status in {"running", "queued"}:
        run.cancel_requested = True
        session.commit()
    return CancelResponse(runId=run.id)


@admin_router.get("/runs", response_model=RunListResponse)
def admin_list_runs(
    _: UserPrincipal = Depends(require_unified_admin),
    session: Session = Depends(get_db),
):
    runs = list(
        session.scalars(
            select(AgentRun)
            .options(selectinload(AgentRun.steps), selectinload(AgentRun.traces))
            .order_by(AgentRun.created_at.desc())
            .limit(100)
        )
    )
    items = []
    for run in runs:
        view = run_view(run)
        view["outputText"] = ""
        view["inputText"] = ""
        items.append(RunView.model_validate(view))
    return RunListResponse(items=items)
