from datetime import timezone

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.errors import APIError
from app.db import get_db
from app.models import Conversation
from app.modules.identity.dependencies import (
    require_active_user,
    require_authenticated,
    require_creator,
    require_trusted_origin,
    require_unified_admin,
    require_user_csrf,
)
from app.modules.identity.schemas import (
    AdminUserListResponse,
    ClaimLegacyRequest,
    ClaimLegacyResponse,
    LoginRequest,
    LoginResponse,
    MeStatusResponse,
    ModerationRequest,
    ModerationResponse,
    PasswordChangeRequest,
    RecoveryCompleteRequest,
    RecoveryCompleteResponse,
    RecoveryMaterial,
    RecoveryRotateRequest,
    RegisterRequest,
    RegisterResponse,
    RoleUpdateRequest,
    SessionInfo,
    SessionResponse,
    UserView,
)
from app.modules.identity.user_service import UserIdentityService, UserPrincipal, user_view
from app.owner import require_json_request, verified_owner_id
from app.repositories import utc_now

auth_router = APIRouter(prefix="/auth", tags=["auth"])
me_router = APIRouter(prefix="/me", tags=["me"])
admin_router = APIRouter(prefix="/admin/users", tags=["admin-users"])


def _csrf_token(request: Request) -> str:
    return request.headers.get("x-csrf-token", "")


def _set_session_cookies(
    response: Response, token: str, csrf_token: str, *, max_age: int, secure: bool
) -> None:
    response.set_cookie(
        settings.user_session_cookie_name,
        token,
        max_age=max_age,
        httponly=True,
        samesite="strict",
        secure=secure,
        path="/",
    )
    response.set_cookie(
        settings.user_csrf_cookie_name,
        csrf_token,
        max_age=max_age,
        httponly=False,
        samesite="strict",
        secure=secure,
        path="/",
    )


def _clear_session_cookies(response: Response) -> None:
    secure = settings.user_cookie_secure
    response.delete_cookie(
        settings.user_session_cookie_name,
        path="/",
        secure=secure,
        httponly=True,
        samesite="strict",
    )
    response.delete_cookie(
        settings.user_csrf_cookie_name,
        path="/",
        secure=secure,
        httponly=False,
        samesite="strict",
    )


def _session_info(principal: UserPrincipal) -> SessionInfo:
    return SessionInfo(
        scope=principal.session.scope,
        expiresAt=principal.session.expires_at.replace(tzinfo=timezone.utc),
    )


@auth_router.post("/register", response_model=RegisterResponse, status_code=201)
def register(
    payload: RegisterRequest,
    request: Request,
    session: Session = Depends(get_db),
):
    require_json_request(request)
    require_trusted_origin(request)
    data, code = UserIdentityService(session).register(
        payload,
        idempotency_key=request.headers.get("idempotency-key", ""),
        client_ip=request.client.host if request.client else "",
    )
    recovery = (
        RecoveryMaterial(code=code, issuedAt=utc_now().replace(tzinfo=timezone.utc))
        if code
        else None
    )
    return RegisterResponse(
        user=UserView.model_validate(data["user"]),
        recovery=recovery,
        sessionIssued=False,
        replayed=bool(data.get("replayed")),
    )


@auth_router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: Session = Depends(get_db),
):
    require_json_request(request)
    require_trusted_origin(request)
    issued = UserIdentityService(session).login(
        payload.accountNumber,
        payload.password,
        client_ip=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
    )
    max_age = int(
        (
            issued.principal.session.expires_at - issued.principal.session.created_at
        ).total_seconds()
    )
    _set_session_cookies(
        response,
        issued.token,
        issued.csrf_token,
        max_age=max_age,
        secure=settings.user_cookie_secure,
    )
    return LoginResponse(
        authenticated=True,
        user=user_view(issued.principal.user),
        session=_session_info(issued.principal),
    )


@auth_router.get("/session", response_model=SessionResponse)
def get_session(principal: UserPrincipal = Depends(require_authenticated)):
    return SessionResponse(
        authenticated=True,
        user=user_view(principal.user),
        session=_session_info(principal),
    )


@auth_router.post("/logout", status_code=204)
def logout(
    request: Request,
    response: Response,
    principal: UserPrincipal = Depends(require_authenticated),
    session: Session = Depends(get_db),
):
    require_user_csrf(request, principal)
    UserIdentityService(session).logout(
        principal, client_ip=request.client.host if request.client else ""
    )
    _clear_session_cookies(response)
    response.status_code = 204
    return response


@auth_router.post("/password/change", response_model=RecoveryCompleteResponse)
def change_password(
    payload: PasswordChangeRequest,
    request: Request,
    principal: UserPrincipal = Depends(require_active_user),
    session: Session = Depends(get_db),
):
    require_json_request(request)
    require_user_csrf(request, principal)
    code = UserIdentityService(session).change_password(
        principal,
        payload.currentPassword,
        payload.newPassword,
        payload.newPasswordConfirm,
    )
    return RecoveryCompleteResponse(
        recovery=RecoveryMaterial(code=code, issuedAt=utc_now().replace(tzinfo=timezone.utc))
    )


@auth_router.post("/recovery/complete", response_model=RecoveryCompleteResponse)
def complete_recovery(
    payload: RecoveryCompleteRequest,
    request: Request,
    session: Session = Depends(get_db),
):
    require_json_request(request)
    require_trusted_origin(request)
    code = UserIdentityService(session).complete_recovery(
        payload.accountNumber,
        payload.recoveryCode,
        payload.newPassword,
        payload.newPasswordConfirm,
        client_ip=request.client.host if request.client else "",
    )
    return RecoveryCompleteResponse(
        recovery=RecoveryMaterial(code=code, issuedAt=utc_now().replace(tzinfo=timezone.utc))
    )


@auth_router.post("/recovery/rotate", response_model=RecoveryCompleteResponse)
def rotate_recovery(
    payload: RecoveryRotateRequest,
    request: Request,
    principal: UserPrincipal = Depends(require_active_user),
    session: Session = Depends(get_db),
):
    require_json_request(request)
    require_user_csrf(request, principal)
    code = UserIdentityService(session).rotate_recovery_code(
        principal, payload.currentPassword
    )
    return RecoveryCompleteResponse(
        recovery=RecoveryMaterial(code=code, issuedAt=utc_now().replace(tzinfo=timezone.utc))
    )


@me_router.get("/status", response_model=MeStatusResponse)
def my_status(principal: UserPrincipal = Depends(require_authenticated)):
    return MeStatusResponse(
        user=user_view(principal.user),
        canUseService=principal.user.status == "ACTIVE" and principal.session.scope == "FULL",
    )


@me_router.get("")
def my_profile(principal: UserPrincipal = Depends(require_active_user)):
    return {"user": user_view(principal.user)}


@me_router.post("/legacy-conversations/claim", response_model=ClaimLegacyResponse)
def claim_legacy_conversations(
    payload: ClaimLegacyRequest,
    request: Request,
    principal: UserPrincipal = Depends(require_active_user),
    session: Session = Depends(get_db),
):
    require_json_request(request)
    require_user_csrf(request, principal)
    owner_id = verified_owner_id(request)
    if not owner_id:
        raise APIError(400, "BAD_REQUEST", "缺少可用于认领的匿名会话签名")
    statement = select(Conversation).where(
        Conversation.owner_id == owner_id, Conversation.user_id.is_(None)
    )
    if payload.conversationIds:
        statement = statement.where(Conversation.id.in_(payload.conversationIds))
    candidates = list(session.scalars(statement.limit(500)))
    claimed: list[str] = []
    now = utc_now()
    for conversation in candidates:
        conversation.user_id = principal.user.id
        conversation.updated_at = now
        claimed.append(conversation.id)
    session.commit()
    requested = len(payload.conversationIds)
    skipped = max(requested - len(claimed), 0) if requested else 0
    return ClaimLegacyResponse(
        claimed=len(claimed), skipped=skipped, conversationIds=claimed
    )


@admin_router.get("", response_model=AdminUserListResponse)
def list_users(
    status: str | None = Query(default=None, max_length=16),
    role: str | None = Query(default=None, max_length=16),
    q: str = Query(default="", max_length=80),
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = None,
    _: UserPrincipal = Depends(require_unified_admin),
    session: Session = Depends(get_db),
):
    users, total, next_cursor = UserIdentityService(session).list_users(
        status=status, role=role, query=q, limit=limit, cursor=cursor
    )
    return AdminUserListResponse(
        items=[user_view(item) for item in users],
        total=total,
        nextCursor=next_cursor,
    )


@admin_router.get("/{user_id}", response_model=UserView)
def get_user(
    user_id: str,
    _: UserPrincipal = Depends(require_unified_admin),
    session: Session = Depends(get_db),
):
    return user_view(UserIdentityService(session).get_user(user_id))


def _moderate(
    user_id: str,
    action: str,
    payload: ModerationRequest,
    request: Request,
    principal: UserPrincipal,
    session: Session,
) -> ModerationResponse:
    require_json_request(request)
    require_user_csrf(request, principal)
    user, audit_id = UserIdentityService(session).moderate(
        user_id,
        action,
        expected_version=payload.expectedVersion,
        reason=payload.reason,
        actor_id=principal.user.id,
        client_ip=request.client.host if request.client else "",
    )
    return ModerationResponse(user=user_view(user), auditEventId=audit_id)


@admin_router.post("/{user_id}/activate", response_model=ModerationResponse)
def activate_user(
    user_id: str,
    payload: ModerationRequest,
    request: Request,
    principal: UserPrincipal = Depends(require_unified_admin),
    session: Session = Depends(get_db),
):
    return _moderate(user_id, "activate", payload, request, principal, session)


@admin_router.post("/{user_id}/reject", response_model=ModerationResponse)
def reject_user(
    user_id: str,
    payload: ModerationRequest,
    request: Request,
    principal: UserPrincipal = Depends(require_unified_admin),
    session: Session = Depends(get_db),
):
    return _moderate(user_id, "reject", payload, request, principal, session)


@admin_router.post("/{user_id}/disable", response_model=ModerationResponse)
def disable_user(
    user_id: str,
    payload: ModerationRequest,
    request: Request,
    principal: UserPrincipal = Depends(require_unified_admin),
    session: Session = Depends(get_db),
):
    return _moderate(user_id, "disable", payload, request, principal, session)


@admin_router.post("/{user_id}/restore", response_model=ModerationResponse)
def restore_user(
    user_id: str,
    payload: ModerationRequest,
    request: Request,
    principal: UserPrincipal = Depends(require_unified_admin),
    session: Session = Depends(get_db),
):
    return _moderate(user_id, "restore", payload, request, principal, session)


@admin_router.patch("/{user_id}/roles", response_model=ModerationResponse)
def set_user_role(
    user_id: str,
    payload: RoleUpdateRequest,
    request: Request,
    principal: UserPrincipal = Depends(require_unified_admin),
    session: Session = Depends(get_db),
):
    require_json_request(request)
    require_user_csrf(request, principal)
    user, audit_id = UserIdentityService(session).set_role(
        user_id,
        payload.role,
        expected_version=payload.expectedVersion,
        reason=payload.reason,
        actor_id=principal.user.id,
        client_ip=request.client.host if request.client else "",
    )
    return ModerationResponse(user=user_view(user), auditEventId=audit_id)
