from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    client_request_id: UUID
    model: str | None = Field(default=None, min_length=1, max_length=100)


class GenerationRequest(BaseModel):
    client_request_id: UUID


class StopGenerationRequest(BaseModel):
    assistant_message_id: UUID | None = None


class StopGenerationData(BaseModel):
    conversation_id: UUID
    assistant_message_id: UUID
    status: Literal["cancellation_requested", "cancelled", "already_terminal"]
