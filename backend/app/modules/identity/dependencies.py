from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import hash_token
from app.db import get_db
from app.modules.identity.service import AdminIdentityService, AdminPrincipal
from app.modules.identity.user_service import UserIdentityService, UserPrincipal


def require_admin(
    request: Request, session: Session = Depends(get_db)
) -> AdminPrincipal:
    principal = AdminIdentityService(session).resolve(
        request.cookies.get(settings.admin_session_cookie_name)
    )
    if principal is None:
        raise HTTPException(status_code=401, detail="Administrator login required")
    if principal.user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator permission required")
    return principal


def require_trusted_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin:
        expected = f"{request.url.scheme}://{request.headers.get('host', '')}".rstrip("/")
        allowed = settings.allowed_origin_values | {expected}
        if origin.rstrip("/") not in allowed:
            raise HTTPException(status_code=403, detail="Origin not allowed")
        return
    fetch_site = request.headers.get("sec-fetch-site", "").lower()
    if fetch_site not in {"same-origin", "none"}:
        raise HTTPException(status_code=403, detail="Origin header required")


def require_csrf(request: Request, principal: AdminPrincipal) -> None:
    require_trusted_origin(request)
    token = request.headers.get("x-csrf-token", "")
    if not token or not (hash_token(token) == principal.session.csrf_hash):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")


def get_optional_user(
    request: Request, session: Session = Depends(get_db)
) -> UserPrincipal | None:
    return UserIdentityService(session).resolve_session(
        request.cookies.get(settings.user_session_cookie_name)
    )


def require_authenticated(
    principal: UserPrincipal | None = Depends(get_optional_user),
) -> UserPrincipal:
    if principal is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return principal


def require_active_user(
    principal: UserPrincipal = Depends(require_authenticated),
) -> UserPrincipal:
    if principal.user.status != "ACTIVE" or principal.session.scope != "FULL":
        raise HTTPException(status_code=403, detail="Account is not active")
    return principal


def require_creator(
    principal: UserPrincipal = Depends(require_active_user),
) -> UserPrincipal:
    if principal.user.role not in {"CREATOR", "ADMIN"}:
        raise HTTPException(status_code=403, detail="Creator permission required")
    return principal


def require_unified_admin(
    principal: UserPrincipal = Depends(require_active_user),
) -> UserPrincipal:
    if principal.user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Administrator permission required")
    return principal


def require_user_csrf(request: Request, principal: UserPrincipal) -> None:
    require_trusted_origin(request)
    token = request.headers.get("x-csrf-token", "")
    if not token or not (hash_token(token) == principal.session.csrf_hash):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")
