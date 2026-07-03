from __future__ import annotations

from pydantic import BaseModel, Field


class PortfolioChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: str | None = Field(default=None, min_length=1, max_length=128)


class PortfolioChatData(BaseModel):
    reply: str
    session_id: str


class ChatMessage(BaseModel):
    role: str
    content: str
