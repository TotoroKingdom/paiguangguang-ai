from dataclasses import dataclass, field
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse


@dataclass
class APIError(Exception):
    status_code: int
    code: str
    message: str
    fields: dict[str, Any] = field(default_factory=dict)
    retry_after_seconds: int | None = None

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


async def api_error_handler(_: Request, exc: APIError) -> JSONResponse:
    headers: dict[str, str] = {}
    if exc.retry_after_seconds is not None:
        headers["Retry-After"] = str(exc.retry_after_seconds)
    return JSONResponse(
        status_code=exc.status_code,
        headers=headers,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "fields": exc.fields,
            }
        },
    )
