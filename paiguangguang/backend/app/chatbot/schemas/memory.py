from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


MemoryStatus = Literal["candidate", "active", "superseded", "deleted", "failed"]


class MemoryData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID | None = None
    memory_type: Literal["preference", "goal", "project_context", "explicit", "fact", "work_context"]
    content: str
    importance: float
    confidence: float
    source_message_ids: list[UUID]
    status: MemoryStatus
    last_accessed_at: datetime | None = None
    expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class MemoryPageData(BaseModel):
    items: list[MemoryData]
    next_cursor: str | None
    has_more: bool


class MemoryUpdateRequest(BaseModel):
    content: str | None = Field(default=None, min_length=1, max_length=4000)
    status: Literal["candidate", "active"] | None = None
    expires_at: datetime | None = None

