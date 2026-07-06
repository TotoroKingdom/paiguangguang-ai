from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

DataT = TypeVar("DataT")


class ErrorDetail(BaseModel):
    code: str
    message: str


class ApiResponse(BaseModel, Generic[DataT]):
    success: bool = True
    data: DataT | None = None
    error: ErrorDetail | None = None


class HealthData(BaseModel):
    status: str
    cache_backend: str | None = None
    knowledge_base_version: str | None = None
