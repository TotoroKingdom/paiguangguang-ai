from datetime import timezone

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.modules.identity.dependencies import require_admin, require_trusted_origin
from app.modules.identity.schemas import (
    AdminLoginRequest,
    AdminSessionResponse,
    AdminUserView,
)
from app.modules.identity.service import AdminIdentityService, AdminPrincipal
from app.modules.observability.service import record_audit
from app.owner import require_json_request

router = APIRouter(prefix="/admin/auth", tags=["admin-auth"])


def _user_view(principal: AdminPrincipal) -> AdminUserView:
    return AdminUserView(
        id=principal.user.id,
        username=principal.user.username,
        role="admin" if principal.user.role == "admin" else "viewer",
        expiresAt=principal.session.expires_at.replace(tzinfo=timezone.utc),
    )


def _set_session_cookies(response: Response, token: str, csrf_token: str) -> None:
    max_age = settings.admin_session_max_age_seconds
    response.set_cookie(
        settings.admin_session_cookie_name,
        token,
        max_age=max_age,
        httponly=True,
        samesite="strict",
        secure=settings.admin_cookie_secure,
        path="/",
    )
    response.set_cookie(
        settings.admin_csrf_cookie_name,
        csrf_token,
        max_age=max_age,
        httponly=False,
        samesite="strict",
        secure=settings.admin_cookie_secure,
        path="/",
    )


def _clear_session_cookies(response: Response) -> None:
    response.delete_cookie(
        settings.admin_session_cookie_name,
        path="/",
        secure=settings.admin_cookie_secure,
        httponly=True,
        samesite="strict",
    )
    response.delete_cookie(
        settings.admin_csrf_cookie_name,
        path="/",
        secure=settings.admin_cookie_secure,
        httponly=False,
        samesite="strict",
    )


@router.post("/login", response_model=AdminSessionResponse)
def login(
    payload: AdminLoginRequest,
    request: Request,
    response: Response,
    session: Session = Depends(get_db),
):
    require_json_request(request)
    require_trusted_origin(request)
    created = AdminIdentityService(session).login(
        payload.username,
        payload.password,
        client_ip=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
    )
    record_audit(
        session,
        actor_type="admin",
        actor_id=created.principal.user.id,
        action="admin.login",
        resource_type="admin_session",
        resource_id=created.principal.session.id,
        client_ip=request.client.host if request.client else "",
    )
    session.commit()
    _set_session_cookies(response, created.token, created.csrf_token)
    return AdminSessionResponse(authenticated=True, user=_user_view(created.principal))


@router.get("/session", response_model=AdminSessionResponse)
def get_session(principal: AdminPrincipal = Depends(require_admin)):
    return AdminSessionResponse(authenticated=True, user=_user_view(principal))


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    response: Response,
    principal: AdminPrincipal = Depends(require_admin),
    session: Session = Depends(get_db),
):
    from app.modules.identity.dependencies import require_csrf

    require_csrf(request, principal)
    record_audit(
        session,
        actor_type="admin",
        actor_id=principal.user.id,
        action="admin.logout",
        resource_type="admin_session",
        resource_id=principal.session.id,
        client_ip=request.client.host if request.client else "",
    )
    AdminIdentityService(session).logout(principal)
    _clear_session_cookies(response)
    response.status_code = 204
    return response
