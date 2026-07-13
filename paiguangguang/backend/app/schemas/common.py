from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

from app.core.request_id import get_request_id

DataT = TypeVar("DataT")


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ApiResponse(BaseModel, Generic[DataT]):
    success: bool = True
    data: DataT | None = None
    error: ErrorDetail | None = None
    request_id: str = Field(default_factory=get_request_id)


class HealthData(BaseModel):
    status: str
    cache_backend: str | None = None
    knowledge_base_version: str | None = None
