from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.schemas.task import TaskEventData, TaskStateData
from app.storage.task_store import InMemoryTaskStore, RedisTaskStore, get_task_store


class TaskService:
    def __init__(self, task_store: InMemoryTaskStore | RedisTaskStore | None = None) -> None:
        self.task_store = task_store or get_task_store()

    def start_task(
        self,
        *,
        task_type: str,
        title: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        state = self.task_store.create_task(task_type=task_type, title=title, metadata=metadata)
        self.task_store.append_event(
            state.task_id,
            event_type="status_changed",
            message="Task started",
            status="running",
            payload={
                "task_type": task_type,
                "title": title,
                "metadata": dict(metadata or {}),
            },
        )
        return state.task_id

    def record_step(
        self,
        task_id: str,
        *,
        step: Mapping[str, Any],
        index: int | None = None,
        total: int | None = None,
    ) -> TaskEventData:
        payload = dict(step)
        if index is not None:
            payload["step_index"] = index
        if total is not None:
            payload["total_steps"] = total

        progress: float | None = None
        if index is not None and total:
            progress = min(0.99, index / max(total, 1))

        return self.task_store.append_event(
            task_id,
            event_type="progress",
            message=str(step.get("title", "Task step")),
            status="running",
            payload=payload,
            progress=progress,
            current_step=str(step.get("title")) if step.get("title") is not None else None,
        )

    def complete_task(
        self,
        task_id: str,
        *,
        output: Mapping[str, Any],
        message: str = "Task completed",
    ) -> TaskEventData:
        return self.task_store.append_event(
            task_id,
            event_type="output",
            message=message,
            status="completed",
            payload={"output": dict(output)},
            output=dict(output),
            progress=1.0,
        )

    def fail_task(
        self,
        task_id: str,
        *,
        message: str,
        error: str,
        payload: dict[str, Any] | None = None,
    ) -> TaskEventData:
        return self.task_store.append_event(
            task_id,
            event_type="failed",
            message=message,
            status="failed",
            payload=payload or {"error": error},
            error=error,
        )

    def get_task(self, task_id: str) -> TaskStateData | None:
        return self.task_store.get_task(task_id)

    def get_events(self, task_id: str) -> list[TaskEventData]:
        return self.task_store.get_events(task_id)


_TASK_SERVICE = TaskService()


def get_task_service() -> TaskService:
    return _TASK_SERVICE
