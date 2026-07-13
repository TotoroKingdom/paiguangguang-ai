from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.chatbot.schemas.message import MessageData


ChatTurnStatus = Literal["pending", "streaming", "completed", "failed", "cancelled"]


class ChatCompleteRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    client_request_id: UUID


class ChatLLMRunData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    request_id: str
    provider: str
    model: str
    prompt_version: str
    status: ChatTurnStatus
    attempt_count: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: int | None
    first_token_latency_ms: int | None
    finish_reason: str | None
    error_code: str | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ChatCompletionData(BaseModel):
    conversation_id: UUID
    client_request_id: UUID
    replayed: bool = False
    user_message: MessageData
    assistant_message: MessageData
    llm_run: ChatLLMRunData
