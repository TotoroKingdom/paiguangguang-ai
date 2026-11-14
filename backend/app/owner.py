import base64
import hashlib
import hmac
import secrets

from fastapi import Cookie, HTTPException, Request, Response

from app.config import settings


def _sign(owner_id: str) -> str:
    digest = hmac.new(
        settings.owner_cookie_secret.encode("utf-8"), owner_id.encode("utf-8"), hashlib.sha256
    ).digest()
    return f"{owner_id}.{base64.urlsafe_b64encode(digest).decode('ascii').rstrip('=')}"


def _verify(value: str) -> str | None:
    try:
        owner_id, signature = value.split(".", 1)
    except ValueError:
        return None
    if len(owner_id) != 32 or not all(char.isalnum() or char in "-_" for char in owner_id):
        return None
    expected = _sign(owner_id).split(".", 1)[1]
    if not hmac.compare_digest(signature, expected):
        return None
    return owner_id


def get_owner_id(request: Request, response: Response) -> str:
    owner_id = verified_owner_id(request)
    if owner_id is None:
        owner_id = secrets.token_urlsafe(24)[:32]
        response.set_cookie(
            settings.owner_cookie_name,
            _sign(owner_id),
            max_age=settings.owner_cookie_max_age,
            httponly=True,
            samesite="lax",
            secure=settings.owner_cookie_secure,
            path="/",
        )
    return owner_id


def verified_owner_id(request: Request) -> str | None:
    value = request.cookies.get(settings.owner_cookie_name)
    return _verify(value) if value else None


def require_json_request(request: Request) -> None:
    content_type = request.headers.get("content-type", "")
    if not content_type.lower().startswith("application/json"):
        raise HTTPException(status_code=415, detail="JSON request body required")

