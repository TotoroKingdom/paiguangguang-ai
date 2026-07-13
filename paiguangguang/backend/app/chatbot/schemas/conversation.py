from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, model_validator

from app.chatbot.schemas.common import (
    ConversationActiveGenerationData,
    ConversationStatus,
    ConversationTitleSource,
    DeleteResultData,
)


class ConversationCreateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    model: str | None = Field(default=None, min_length=1, max_length=100)


class ConversationUpdateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    model: str | None = Field(default=None, min_length=1, max_length=100)

    @model_validator(mode="after")
    def ensure_at_least_one_field(self) -> "ConversationUpdateRequest":
        if self.title is None and self.model is None:
            raise ValueError("At least one field must be provided")
        return self


class ConversationData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    title_source: ConversationTitleSource
    status: ConversationStatus
    model: str
    last_message_at: datetime
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


class ConversationDetailData(ConversationData):
    active_generation: ConversationActiveGenerationData | None = None


class ConversationPageData(BaseModel):
    items: list[ConversationData]
    next_cursor: str | None
    has_more: bool

