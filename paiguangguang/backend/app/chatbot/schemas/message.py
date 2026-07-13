from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MessageData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    role: str
    content: str
    content_json: dict[str, Any] | None = None
    sequence_number: int
    status: str
    model: str | None = None
    parent_message_id: UUID | None = None
    client_request_id: UUID | None = None
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    error_code: str | None = None
    created_at: datetime
    updated_at: datetime


class MessagePageData(BaseModel):
    items: list[MessageData]
    next_cursor: str | None = None
    has_more: bool

