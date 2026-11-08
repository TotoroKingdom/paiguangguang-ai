from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.db import get_db
from app.modules.capabilities.models import (
    CapabilityDefinition,
    CapabilityRun,
    CapabilityVersion,
)
from app.modules.capabilities.schemas import (
    AuditItem,
    AuditListResponse,
    CapabilityCreate,
    CapabilityDetail,
    CapabilityListResponse,
    CapabilityUpdate,
    KindCount,
    OverviewResponse,
    PublicCapability,
    PublicCapabilityListResponse,
    PublishRequest,
    ReleaseItem,
    ReleaseListResponse,
    RunItem,
    RunListResponse,
    SettingsResponse,
    ReviewActionRequest,
    ReviewEventView,
    ReviewListResponse,
    GrantRequest,
)
from app.modules.capabilities.service import (
    CapabilityService,
    decode_cursor,
    encode_cursor,
    loads,
    run_count,
)
from app.modules.identity.dependencies import (
    require_admin,
    require_csrf,
    require_creator,
    require_unified_admin,
    require_user_csrf,
)
from app.modules.identity.user_service import UserIdentityService
from app.modules.identity.user_service import UserPrincipal
from app.modules.identity.service import AdminPrincipal
from app.modules.observability.models import AuditEvent
from app.modules.observability.service import record_audit
from app.owner import require_json_request

public_router = APIRouter(prefix="/capabilities", tags=["capabilities"])
admin_router = APIRouter(prefix="/admin", tags=["admin-capabilities"])
creator_router = APIRouter(prefix="/creator", tags=["creator-capabilities"])
governance_router = APIRouter(prefix="/admin/governance", tags=["admin-governance"])


def catalog_user_id(request: Request, session: Session) -> str | None:
    token = request.cookies.get(settings.user_session_cookie_name)
    if not token:
        return None
    principal = UserIdentityService(session).resolve_session(token)
    return principal.user.id if principal else None


@public_router.get("", response_model=PublicCapabilityListResponse)
def list_public_capabilities(
    request: Request,
    kind: str | None = Query(default=None, pattern="^(tool|skill|mcp|agent)$"),
    q: str = Query(default="", max_length=120),
    session: Session = Depends(get_db),
):
    return PublicCapabilityListResponse(
        items=CapabilityService(session).public_list(
            kind=kind, query=q, user_id=catalog_user_id(request, session)
        )
    )


@public_router.get("/{capability_id}", response_model=PublicCapability)
def get_public_capability(
    capability_id: str, request: Request, session: Session = Depends(get_db)
):
    try:
        return CapabilityService(session).public_capability(
            capability_id, catalog_user_id(request, session)
        )
    except HTTPException as error:
        raise HTTPException(status_code=404, detail="Capability not found") from error


def _audit_item(event: AuditEvent) -> AuditItem:
    return AuditItem(
        id=event.id,
        actorType=event.actor_type,
        actorId=event.actor_id,
        action=event.action,
        resourceType=event.resource_type,
        resourceId=event.resource_id,
        detail=loads(event.detail_json, {}),
        createdAt=event.created_at.replace(tzinfo=timezone.utc),
    )


def _run_item(
    run: CapabilityRun, definition: CapabilityDefinition | None
) -> RunItem:
    detail = loads(run.detail_json, {})
    return RunItem(
        id=run.id,
        capabilityId=run.capability_id,
        capabilityName=str(detail.get("capabilityName") or (definition.name if definition else run.capability_id)),
        kind=definition.kind if definition is not None else None,
        version=run.version,
        conversationId=run.conversation_id,
        mode=run.mode,
        status=run.status,
        createdAt=run.created_at.replace(tzinfo=timezone.utc),
    )


@admin_router.get("/overview", response_model=OverviewResponse)
def overview(
    principal: AdminPrincipal = Depends(require_admin),
    session: Session = Depends(get_db),
):
    counts: list[KindCount] = []
    for kind in ("tool", "skill", "mcp", "agent"):
        definitions = list(
            session.scalars(
                select(CapabilityDefinition).where(CapabilityDefinition.kind == kind)
            )
        )
        counts.append(
            KindCount(
                kind=kind,
                total=len(definitions),
                published=sum(item.status == "published" for item in definitions),
                draft=sum(item.status == "draft" for item in definitions),
                disabled=sum(item.status == "disabled" for item in definitions),
            )
        )
    recent_runs = list(
        session.scalars(
            select(CapabilityRun).order_by(CapabilityRun.created_at.desc()).limit(6)
        )
    )
    definitions = {
        item.id: item
        for item in session.scalars(
            select(CapabilityDefinition).where(
                CapabilityDefinition.id.in_([run.capability_id for run in recent_runs])
            )
        )
    } if recent_runs else {}
    recent_audit = list(
        session.scalars(
            select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(8)
        )
    )
    return OverviewResponse(
        capabilities=counts,
        totalRuns=run_count(session),
        recentRuns=[_run_item(run, definitions.get(run.capability_id)) for run in recent_runs],
        recentAudit=[_audit_item(event) for event in recent_audit],
        admin={
            "username": principal.user.username,
            "role": principal.user.role,
            "sessionExpiresAt": principal.session.expires_at.replace(
                tzinfo=timezone.utc
            ).isoformat(),
        },
        environment=settings.environment,
    )


@admin_router.get("/capabilities", response_model=CapabilityListResponse)
def list_capabilities(
    kind: str | None = Query(default=None, pattern="^(tool|skill|mcp|agent)$"),
    status: str | None = Query(default=None, pattern="^(draft|published|disabled)$"),
    q: str = Query(default="", max_length=120),
    _: AdminPrincipal = Depends(require_admin),
    session: Session = Depends(get_db),
):
    return CapabilityListResponse(
        items=CapabilityService(session).list(kind=kind, status=status, query=q)
    )


@admin_router.post("/capabilities", response_model=CapabilityDetail, status_code=201)
def create_capability(
    payload: CapabilityCreate,
    request: Request,
    principal: AdminPrincipal = Depends(require_admin),
    session: Session = Depends(get_db),
):
    require_json_request(request)
    require_csrf(request, principal)
    detail = CapabilityService(session).create(payload, actor_id=principal.user.id)
    record_audit(
        session,
        actor_type="admin",
        actor_id=principal.user.id,
        action="capability.created",
        resource_type="capability",
        resource_id=detail.id,
        detail={"kind": detail.kind, "name": detail.name},
        client_ip=request.client.host if request.client else "",
    )
    session.commit()
    return detail


@admin_router.get("/capabilities/{capability_id}", response_model=CapabilityDetail)
def get_capability(
    capability_id: str,
    _: AdminPrincipal = Depends(require_admin),
    session: Session = Depends(get_db),
):
    return CapabilityService(session).detail(capability_id)


@admin_router.patch("/capabilities/{capability_id}", response_model=CapabilityDetail)
def update_capability(
    capability_id: str,
    payload: CapabilityUpdate,
    request: Request,
    principal: AdminPrincipal = Depends(require_admin),
    session: Session = Depends(get_db),
):
    require_json_request(request)
    require_csrf(request, principal)
    detail = CapabilityService(session).update(
        capability_id, payload, actor_id=principal.user.id
    )
    record_audit(
        session,
        actor_type="admin",
        actor_id=principal.user.id,
        action="capability.draft.saved",
        resource_type="capability",
        resource_id=detail.id,
        detail={
            "kind": detail.kind,
            "name": detail.name,
            "draftVersion": detail.draftVersion,
        },
        client_ip=request.client.host if request.client else "",
    )
    session.commit()
    return detail


@admin_router.post(
    "/capabilities/{capability_id}/publish", response_model=CapabilityDetail
)
def publish_capability(
    capability_id: str,
    payload: PublishRequest,
    request: Request,
    principal: AdminPrincipal = Depends(require_admin),
    session: Session = Depends(get_db),
):
    require_json_request(request)
    require_csrf(request, principal)
    detail = CapabilityService(session).publish(
        capability_id,
        version_id=payload.versionId,
        changelog=payload.changelog,
        actor_id=principal.user.id,
    )
    record_audit(
        session,
        actor_type="admin",
        actor_id=principal.user.id,
        action="capability.published",
        resource_type="capability",
        resource_id=detail.id,
        detail={
            "kind": detail.kind,
            "name": detail.name,
            "version": detail.publishedVersion,
        },
        client_ip=request.client.host if request.client else "",
    )
    session.commit()
    return detail


@admin_router.post(
    "/capabilities/{capability_id}/disable", response_model=CapabilityDetail
)
def disable_capability(
    capability_id: str,
    request: Request,
    principal: AdminPrincipal = Depends(require_admin),
    session: Session = Depends(get_db),
):
    require_json_request(request)
    require_csrf(request, principal)
    detail = CapabilityService(session).disable(
        capability_id, actor_id=principal.user.id
    )
    record_audit(
        session,
        actor_type="admin",
        actor_id=principal.user.id,
        action="capability.disabled",
        resource_type="capability",
        resource_id=detail.id,
        detail={"kind": detail.kind, "name": detail.name},
        client_ip=request.client.host if request.client else "",
    )
    session.commit()
    return detail


@admin_router.get("/releases", response_model=ReleaseListResponse)
def list_releases(
    kind: str | None = Query(default=None, pattern="^(tool|skill|mcp|agent)$"),
    _: AdminPrincipal = Depends(require_admin),
    session: Session = Depends(get_db),
):
    statement = (
        select(CapabilityVersion, CapabilityDefinition)
        .join(
            CapabilityDefinition,
            CapabilityDefinition.id == CapabilityVersion.capability_id,
        )
        .where(CapabilityVersion.status.in_(("published", "retired")))
        .order_by(
            CapabilityVersion.published_at.desc(),
            CapabilityVersion.created_at.desc(),
        )
        .limit(200)
    )
    if kind:
        statement = statement.where(CapabilityDefinition.kind == kind)
    rows = session.execute(statement).all()
    return ReleaseListResponse(
        items=[
            ReleaseItem(
                capabilityId=definition.id,
                capabilityName=definition.name,
                kind=definition.kind,
                versionId=version.id,
                version=version.version,
                status=version.status,
                publishedBy=version.published_by,
                publishedAt=(
                    version.published_at.replace(tzinfo=timezone.utc)
                    if version.published_at
                    else None
                ),
                retiredAt=(
                    version.retired_at.replace(tzinfo=timezone.utc)
                    if version.retired_at
                    else None
                ),
            )
            for version, definition in rows
        ]
    )


@admin_router.get("/runs", response_model=RunListResponse)
def list_runs(
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = None,
    _: AdminPrincipal = Depends(require_admin),
    session: Session = Depends(get_db),
):
    statement = select(CapabilityRun)
    if cursor:
        created_at, row_id = decode_cursor(cursor)
        statement = statement.where(
            (CapabilityRun.created_at < created_at)
            | (
                (CapabilityRun.created_at == created_at)
                & (CapabilityRun.id < row_id)
            )
        )
    runs = list(
        session.scalars(
            statement.order_by(CapabilityRun.created_at.desc(), CapabilityRun.id.desc()).limit(
                limit + 1
            )
        )
    )
    next_cursor = (
        encode_cursor(runs[limit - 1].created_at, runs[limit - 1].id)
        if len(runs) > limit
        else None
    )
    visible = runs[:limit]
    definition_ids = {run.capability_id for run in visible}
    definitions = {
        item.id: item
        for item in session.scalars(
            select(CapabilityDefinition).where(
                CapabilityDefinition.id.in_(definition_ids)
            )
        )
    }
    return RunListResponse(
        items=[_run_item(run, definitions.get(run.capability_id)) for run in visible],
        total=run_count(session),
        nextCursor=next_cursor,
    )


@admin_router.get("/audit-events", response_model=AuditListResponse)
def list_audit_events(
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = None,
    _: AdminPrincipal = Depends(require_admin),
    session: Session = Depends(get_db),
):
    statement = select(AuditEvent)
    if cursor:
        created_at, row_id = decode_cursor(cursor)
        statement = statement.where(
            (AuditEvent.created_at < created_at)
            | ((AuditEvent.created_at == created_at) & (AuditEvent.id < row_id))
        )
    events = list(
        session.scalars(
            statement.order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc()).limit(
                limit + 1
            )
        )
    )
    next_cursor = (
        encode_cursor(events[limit - 1].created_at, events[limit - 1].id)
        if len(events) > limit
        else None
    )
    total = int(session.scalar(select(func.count()).select_from(AuditEvent)) or 0)
    return AuditListResponse(
        items=[_audit_item(event) for event in events[:limit]],
        total=total,
        nextCursor=next_cursor,
    )


@admin_router.get("/settings", response_model=SettingsResponse)
def get_admin_settings(
    principal: AdminPrincipal = Depends(require_admin),
):
    return SettingsResponse(
        environment=settings.environment,
        database=settings.database_url.split("?", 1)[0],
        adminSessionMinutes=settings.admin_session_max_age_seconds // 60,
        secureAdminCookie=settings.admin_cookie_secure,
        allowedOrigins=sorted(settings.allowed_origin_values),
        loginRateLimit={
            "attempts": settings.admin_login_max_attempts,
            "windowSeconds": settings.admin_login_window_seconds,
            "lockSeconds": settings.admin_login_lock_seconds,
        },
        executionMode="simulated-only",
        notes=[
            "当前未接入真实 LLM、MCP Runtime 或 Agent Loop。",
            "管理端能力发布只影响用户端目录与调用准入校验。",
            "匿名浏览器会话继续用于普通聊天，不用于管理员鉴权。",
            f"当前管理员：{principal.user.username}（{principal.user.role}）",
        ],
    )


# --------------------------------------------------------------------- creator
@creator_router.get("/capabilities", response_model=CapabilityListResponse)
def list_creator_capabilities(
    principal: UserPrincipal = Depends(require_creator),
    session: Session = Depends(get_db),
):
    return CapabilityListResponse(
        items=CapabilityService(session).list_owned(principal.user.id)
    )


@creator_router.post("/capabilities", response_model=CapabilityDetail, status_code=201)
def create_creator_capability(
    payload: CapabilityCreate,
    request: Request,
    principal: UserPrincipal = Depends(require_creator),
    session: Session = Depends(get_db),
):
    require_json_request(request)
    require_user_csrf(request, principal)
    detail = CapabilityService(session).create(
        payload,
        actor_id=principal.user.id,
        owner_id=principal.user.id,
        visibility="platform",
        access_mode="granted",
        review_status="draft",
        source="creator",
    )
    record_audit(
        session,
        actor_type="user",
        actor_id=principal.user.id,
        action="creator.capability.created",
        resource_type="capability",
        resource_id=detail.id,
        detail={"kind": detail.kind, "name": detail.name},
        client_ip=request.client.host if request.client else "",
    )
    session.commit()
    return detail


def _owned_capability(
    capability_id: str, principal: UserPrincipal, session: Session
) -> CapabilityDefinition:
    definition = session.scalar(
        select(CapabilityDefinition)
        .where(CapabilityDefinition.id == capability_id)
        .options(selectinload(CapabilityDefinition.versions))
    )
    if definition is None or definition.owner_id != principal.user.id:
        raise HTTPException(status_code=404, detail="Capability not found")
    return definition


@creator_router.patch("/capabilities/{capability_id}", response_model=CapabilityDetail)
def update_creator_capability(
    capability_id: str,
    payload: CapabilityUpdate,
    request: Request,
    principal: UserPrincipal = Depends(require_creator),
    session: Session = Depends(get_db),
):
    require_json_request(request)
    require_user_csrf(request, principal)
    definition = _owned_capability(capability_id, principal, session)
    if definition.status not in {"draft", "published"} or definition.review_status == "submitted":
        raise HTTPException(status_code=409, detail="Capability is not editable")
    detail = CapabilityService(session).update(
        capability_id, payload, actor_id=principal.user.id
    )
    record_audit(
        session,
        actor_type="user",
        actor_id=principal.user.id,
        action="creator.capability.draft.saved",
        resource_type="capability",
        resource_id=detail.id,
        detail={"draftVersion": detail.draftVersion},
        client_ip=request.client.host if request.client else "",
    )
    session.commit()
    return detail


@creator_router.post(
    "/capabilities/{capability_id}/test", response_model=CapabilityDetail
)
def test_creator_capability(
    capability_id: str,
    request: Request,
    principal: UserPrincipal = Depends(require_creator),
    session: Session = Depends(get_db),
):
    require_json_request(request)
    require_user_csrf(request, principal)
    _owned_capability(capability_id, principal, session)
    return CapabilityService(session).test_capability(
        capability_id, actor_id=principal.user.id
    )


@creator_router.post(
    "/capabilities/{capability_id}/submit", response_model=CapabilityDetail
)
def submit_creator_capability(
    capability_id: str,
    payload: ReviewActionRequest,
    request: Request,
    principal: UserPrincipal = Depends(require_creator),
    session: Session = Depends(get_db),
):
    require_json_request(request)
    require_user_csrf(request, principal)
    _owned_capability(capability_id, principal, session)
    detail = CapabilityService(session).submit(
        capability_id, actor_id=principal.user.id, reason=payload.reason
    )
    record_audit(
        session,
        actor_type="user",
        actor_id=principal.user.id,
        action="creator.capability.submitted",
        resource_type="capability",
        resource_id=detail.id,
        client_ip=request.client.host if request.client else "",
    )
    session.commit()
    return detail


# ---------------------------------------------------------- admin governance
@admin_router.get("/reviews", response_model=ReviewListResponse)
def list_reviews(
    _: UserPrincipal = Depends(require_unified_admin),
    session: Session = Depends(get_db),
):
    items = CapabilityService(session).list_reviews()
    return ReviewListResponse(
        items=[
            ReviewEventView(
                id=item.id,
                capabilityId=item.capability_id,
                versionId=item.version_id,
                action=item.action,
                actorId=item.actor_id,
                reason=item.reason,
                createdAt=item.created_at.replace(tzinfo=timezone.utc),
            )
            for item in items
        ]
    )


def _review_capability(
    capability_id: str,
    action: str,
    payload: ReviewActionRequest,
    request: Request,
    principal: UserPrincipal,
    session: Session,
) -> CapabilityDetail:
    require_json_request(request)
    require_user_csrf(request, principal)
    detail = CapabilityService(session).review(
        capability_id, action, actor_id=principal.user.id, reason=payload.reason
    )
    record_audit(
        session,
        actor_type="user",
        actor_id=principal.user.id,
        action=f"admin.capability.{action}",
        resource_type="capability",
        resource_id=detail.id,
        detail={"reason": payload.reason},
        client_ip=request.client.host if request.client else "",
    )
    session.commit()
    return detail


@admin_router.post("/capabilities/{capability_id}/approve", response_model=CapabilityDetail)
def approve_capability(
    capability_id: str,
    payload: ReviewActionRequest,
    request: Request,
    principal: UserPrincipal = Depends(require_unified_admin),
    session: Session = Depends(get_db),
):
    return _review_capability(capability_id, "approve", payload, request, principal, session)


@admin_router.post("/capabilities/{capability_id}/reject", response_model=CapabilityDetail)
def reject_capability(
    capability_id: str,
    payload: ReviewActionRequest,
    request: Request,
    principal: UserPrincipal = Depends(require_unified_admin),
    session: Session = Depends(get_db),
):
    return _review_capability(capability_id, "reject", payload, request, principal, session)


@admin_router.post(
    "/capabilities/{capability_id}/rollback/{version_id}",
    response_model=CapabilityDetail,
)
def rollback_capability(
    capability_id: str,
    version_id: str,
    request: Request,
    principal: UserPrincipal = Depends(require_unified_admin),
    session: Session = Depends(get_db),
):
    require_json_request(request)
    require_user_csrf(request, principal)
    detail = CapabilityService(session).rollback(
        capability_id, version_id, actor_id=principal.user.id
    )
    record_audit(
        session,
        actor_type="user",
        actor_id=principal.user.id,
        action="admin.capability.rollback",
        resource_type="capability",
        resource_id=detail.id,
        detail={"versionId": version_id},
        client_ip=request.client.host if request.client else "",
    )
    session.commit()
    return detail


@admin_router.post("/capabilities/{capability_id}/grants", status_code=204)
def grant_capability(
    capability_id: str,
    payload: GrantRequest,
    request: Request,
    principal: UserPrincipal = Depends(require_unified_admin),
    session: Session = Depends(get_db),
):
    require_json_request(request)
    require_user_csrf(request, principal)
    CapabilityService(session).grant(
        capability_id, payload.userId, actor_id=principal.user.id
    )
    return None


@admin_router.delete("/capabilities/{capability_id}/grants/{user_id}", status_code=204)
def revoke_capability_grant(
    capability_id: str,
    user_id: str,
    request: Request,
    principal: UserPrincipal = Depends(require_unified_admin),
    session: Session = Depends(get_db),
):
    require_user_csrf(request, principal)
    CapabilityService(session).revoke_grant(
        capability_id, user_id, actor_id=principal.user.id
    )
    return None


@governance_router.get("/capabilities", response_model=CapabilityListResponse)
def governance_list_capabilities(
    kind: str | None = Query(default=None, pattern="^(tool|skill|mcp|agent)$"),
    status: str | None = Query(default=None, pattern="^(draft|published|disabled)$"),
    q: str = Query(default="", max_length=120),
    _: UserPrincipal = Depends(require_unified_admin),
    session: Session = Depends(get_db),
):
    return CapabilityListResponse(
        items=CapabilityService(session).list(kind=kind, status=status, query=q)
    )


@governance_router.post(
    "/capabilities/{capability_id}/release", response_model=CapabilityDetail
)
def governance_release_capability(
    capability_id: str,
    payload: PublishRequest,
    request: Request,
    principal: UserPrincipal = Depends(require_unified_admin),
    session: Session = Depends(get_db),
):
    require_json_request(request)
    require_user_csrf(request, principal)
    detail = CapabilityService(session).publish(
        capability_id,
        version_id=payload.versionId,
        changelog=payload.changelog,
        actor_id=principal.user.id,
    )
    record_audit(
        session,
        actor_type="user",
        actor_id=principal.user.id,
        action="admin.capability.released",
        resource_type="capability",
        resource_id=detail.id,
        client_ip=request.client.host if request.client else "",
    )
    session.commit()
    return detail


@governance_router.post(
    "/capabilities/{capability_id}/retire", response_model=CapabilityDetail
)
def governance_retire_capability(
    capability_id: str,
    request: Request,
    principal: UserPrincipal = Depends(require_unified_admin),
    session: Session = Depends(get_db),
):
    require_json_request(request)
    require_user_csrf(request, principal)
    detail = CapabilityService(session).disable(
        capability_id, actor_id=principal.user.id
    )
    record_audit(
        session,
        actor_type="user",
        actor_id=principal.user.id,
        action="admin.capability.retired",
        resource_type="capability",
        resource_id=detail.id,
        client_ip=request.client.host if request.client else "",
    )
    session.commit()
    return detail
