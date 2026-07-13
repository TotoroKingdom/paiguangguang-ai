from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


ChatStreamStatus = Literal["pending", "streaming", "completed", "failed", "cancelled"]
ChatStreamFinalStatus = Literal["completed", "failed", "cancelled"]
ChatStreamEventName = Literal[
    "message.created",
    "message.delta",
    "message.completed",
    "message.failed",
    "message.cancelled",
    "usage.updated",
    "stream.end",
]


class StreamMessageData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sequence_number: int
    status: ChatStreamStatus
    content: str
    model: str | None = None
    updated_at: datetime | None = None


class StreamMessageCreatedData(BaseModel):
    schema_version: Literal["1"] = "1"
    request_id: UUID
    conversation_id: UUID
    assistant_message_id: UUID
    sequence: int
    created_at: datetime
    replayed: bool
    user_message: StreamMessageData
    assistant_message: StreamMessageData


class StreamMessageDeltaData(BaseModel):
    schema_version: Literal["1"] = "1"
    request_id: UUID
    conversation_id: UUID
    assistant_message_id: UUID
    sequence: int
    created_at: datetime
    delta: str
    content_length: int


class StreamCompletedMessageData(BaseModel):
    id: UUID
    status: Literal["completed"] = "completed"
    content: str
    sequence_number: int
    model: str | None = None
    updated_at: datetime


class StreamMessageCompletedData(BaseModel):
    schema_version: Literal["1"] = "1"
    request_id: UUID
    conversation_id: UUID
    assistant_message_id: UUID
    sequence: int
    created_at: datetime
    message: StreamCompletedMessageData
    finish_reason: str | None = None


class StreamErrorData(BaseModel):
    code: str
    message: str
    retryable: bool


class StreamMessageFailedData(BaseModel):
    schema_version: Literal["1"] = "1"
    request_id: UUID
    conversation_id: UUID
    assistant_message_id: UUID
    sequence: int
    created_at: datetime
    error: StreamErrorData
    partial: bool
    content: str


class StreamMessageCancelledData(BaseModel):
    schema_version: Literal["1"] = "1"
    request_id: UUID
    conversation_id: UUID
    assistant_message_id: UUID
    sequence: int
    created_at: datetime
    reason: Literal["user_requested"] = "user_requested"
    content: str


class StreamUsageUpdatedData(BaseModel):
    schema_version: Literal["1"] = "1"
    request_id: UUID
    conversation_id: UUID
    assistant_message_id: UUID
    sequence: int
    created_at: datetime
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    source: Literal["provider", "unknown"]


class StreamEndData(BaseModel):
    schema_version: Literal["1"] = "1"
    request_id: UUID
    conversation_id: UUID
    assistant_message_id: UUID
    sequence: int
    created_at: datetime
    final_status: ChatStreamFinalStatus


@dataclass(frozen=True, slots=True)
class ChatStreamEvent:
    event: ChatStreamEventName
    data: BaseModel
    sequence: int


def encode_chatbot_sse_event(event: ChatStreamEvent) -> str:
    import json

    payload = json.dumps(event.data.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":"))
    return f"id: {event.sequence}\nevent: {event.event}\ndata: {payload}\n\n"


def encode_chatbot_sse_keepalive() -> str:
    return ": keepalive\n\n"
