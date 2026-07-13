from __future__ import annotations

from typing import Any

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.core.request_id import get_request_id


class ServiceError(RuntimeError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ServiceTimeoutError(ServiceError):
    def __init__(self, operation: str, timeout_seconds: float, detail: str | None = None) -> None:
        message = detail or f"{operation} timed out after {timeout_seconds:.1f} seconds"
        super().__init__(message)
        self.operation = operation
        self.timeout_seconds = timeout_seconds


class ServiceRateLimitError(ServiceError):
    def __init__(self, operation: str, limit: int, window_seconds: int) -> None:
        message = f"{operation} is temporarily rate limited. Try again in {window_seconds} seconds."
        super().__init__(message)
        self.operation = operation
        self.limit = limit
        self.window_seconds = window_seconds


class RetrievalFailureError(ServiceError):
    def __init__(self, detail: str) -> None:
        super().__init__(f"Retrieval failed: {detail}")
        self.detail = detail


class ExternalModelError(ServiceError):
    def __init__(self, operation: str, detail: str) -> None:
        super().__init__(f"{operation} failed: {detail}")
        self.operation = operation
        self.detail = detail


def build_error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    details: Any | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    request_id = get_request_id()
    content = jsonable_encoder(
        {
            "success": False,
            "data": None,
            "error": {
                "code": code,
                "message": message,
                "details": details,
            },
            "request_id": request_id,
        }
    )
    response_headers = {"X-Request-ID": request_id}
    if headers:
        response_headers.update(headers)
    return JSONResponse(status_code=status_code, headers=response_headers, content=content)
