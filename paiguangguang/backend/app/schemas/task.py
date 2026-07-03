from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

TaskStatus = Literal["queued", "running", "completed", "failed"]
TaskEventType = Literal["created", "status_changed", "progress", "output", "failed"]


class TaskEventData(BaseModel):
    event_id: str
    sequence: int
    task_id: str
    event_type: TaskEventType
    status: TaskStatus
    message: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class TaskStateData(BaseModel):
    task_id: str
    task_type: str
    title: str
    status: TaskStatus
    message: str | None = None
    progress: float | None = None
    current_step: str | None = None
    event_count: int = 0
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    output: dict[str, Any] | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    latest_event: TaskEventData | None = None
