from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


CapabilityKind = Literal["tool", "skill", "mcp", "agent"]
MessageRole = Literal["user", "assistant"]
MessageStatus = Literal["complete", "generating", "stopped", "error"]


class CapabilityRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=100)
    kind: CapabilityKind
    name: str = Field(min_length=1, max_length=120)


class ExecutionStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=120)
    detail: str = Field(max_length=2000)


class AttachmentSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)


class MessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversationId: str | None = Field(default=None, max_length=36)
    clientTurnId: str | None = Field(default=None, max_length=100)
    text: str = Field(min_length=1, max_length=6000)
    capability: CapabilityRef | None = None
    fileIds: list[str] = Field(default_factory=list, max_length=20)
    simulateFailure: bool = False

    @field_validator("text")
    @classmethod
    def text_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be blank")
        return value


class ConversationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(default="新对话", min_length=1, max_length=80)
    migrationKey: str | None = Field(default=None, max_length=160)

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("title must not be blank")
        return value.strip()


class ConversationRename(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=80)
    version: int = Field(ge=1)

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("title must not be blank")
        return value.strip()


class TurnCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    clientTurnId: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=1, max_length=6000)
    capability: CapabilityRef | None = None
    attachments: list[AttachmentSnapshot] = Field(default_factory=list, max_length=20)
    request: MessageRequest

    @field_validator("text")
    @classmethod
    def text_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be blank")
        return value


class MessagePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(max_length=100_000)
    status: MessageStatus
    steps: list[ExecutionStep] = Field(default_factory=list, max_length=100)
    request: MessageRequest | None = None


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: MessageRole
    content: str
    status: MessageStatus
    steps: list[ExecutionStep]
    capability: CapabilityRef | None
    attachments: list[AttachmentSnapshot]
    request: MessageRequest | None
    clientTurnId: str | None
    createdAt: datetime
    updatedAt: datetime


class ConversationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    createdAt: datetime
    updatedAt: datetime
    version: int


class ConversationResponse(ConversationSummary):
    messages: list[MessageResponse]


class ConversationListResponse(BaseModel):
    items: list[ConversationSummary]
    nextCursor: str | None


class TurnResponse(BaseModel):
    conversation: ConversationSummary
    userMessage: MessageResponse
    assistantMessage: MessageResponse

