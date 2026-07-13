from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


ConversationStatus = Literal["active", "archived", "deleted"]
ConversationTitleSource = Literal["default", "auto", "manual"]


class ConversationActiveGenerationData(BaseModel):
    assistant_message_id: str
    status: str
    started_at: datetime | None = None


class DeleteResultData(BaseModel):
    id: str
    status: Literal["deleted"]
    cleanup_status: Literal["pending", "completed", "retry"]

