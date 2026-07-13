from __future__ import annotations

from contextvars import ContextVar, Token
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

REQUEST_ID_HEADER = "X-Request-ID"
_request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)


def generate_request_id() -> str:
    return str(uuid4())


def get_request_id() -> str:
    request_id = _request_id_context.get()
    if request_id:
        return request_id
    return generate_request_id()


def set_request_id(request_id: str) -> Token[str | None]:
    return _request_id_context.set(request_id)


def reset_request_id(token: Token[str | None]) -> None:
    _request_id_context.reset(token)


def resolve_request_id(request: Request) -> str:
    header_value = request.headers.get(REQUEST_ID_HEADER)
    if header_value:
        return header_value.strip() or generate_request_id()
    return generate_request_id()


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = resolve_request_id(request)
        token = set_request_id(request_id)
        try:
            response = await call_next(request)
        finally:
            reset_request_id(token)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
