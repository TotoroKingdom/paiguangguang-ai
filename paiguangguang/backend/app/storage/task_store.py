from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from threading import Lock
from typing import Any
from uuid import uuid4

from app.core.config import get_settings
from app.schemas.task import TaskEventData, TaskStateData, TaskStatus

try:  # Optional dependency for configured Redis-backed task state.
    import redis  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    redis = None


TERMINAL_STATUSES = {"completed", "failed"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class _TaskRecord:
    task_id: str
    task_type: str
    title: str
    metadata: dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = "queued"
    message: str | None = None
    progress: float | None = None
    current_step: str | None = None
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    completed_at: datetime | None = None
    output: dict[str, Any] | None = None
    error: str | None = None
    events: list[TaskEventData] = field(default_factory=list)
    next_sequence: int = 1

    def append_event(
        self,
        event_type: str,
        *,
        message: str,
        status: TaskStatus,
        payload: dict[str, Any] | None = None,
        progress: float | None = None,
        current_step: str | None = None,
        output: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> TaskEventData:
        now = _now()
        event = TaskEventData(
            event_id=f"{self.task_id}-{self.next_sequence}",
            sequence=self.next_sequence,
            task_id=self.task_id,
            event_type=event_type,  # type: ignore[arg-type]
            status=status,
            message=message,
            payload=payload or {},
            created_at=now,
        )
        self.next_sequence += 1
        self.events.append(event)
        self.status = status
        self.message = message
        if progress is not None:
            self.progress = progress
        if current_step is not None:
            self.current_step = current_step
        if output is not None:
            self.output = output
            self.progress = 1.0
        if error is not None:
            self.error = error
        if status in TERMINAL_STATUSES:
            self.completed_at = now
        self.updated_at = now
        return event

    def to_state(self) -> TaskStateData:
        return TaskStateData(
            task_id=self.task_id,
            task_type=self.task_type,
            title=self.title,
            status=self.status,
            message=self.message,
            progress=self.progress,
            current_step=self.current_step,
            event_count=len(self.events),
            created_at=self.created_at,
            updated_at=self.updated_at,
            completed_at=self.completed_at,
            output=self.output,
            error=self.error,
            metadata=self.metadata,
            latest_event=self.events[-1] if self.events else None,
        )


class InMemoryTaskStore:
    def __init__(self) -> None:
        self._tasks: dict[str, _TaskRecord] = {}
        self._lock = Lock()

    def create_task(
        self,
        *,
        task_type: str,
        title: str,
        metadata: dict[str, Any] | None = None,
    ) -> TaskStateData:
        task_id = str(uuid4())
        record = _TaskRecord(
            task_id=task_id,
            task_type=task_type,
            title=title,
            metadata=dict(metadata or {}),
        )
        record.append_event(
            "created",
            message="Task created",
            status="queued",
            payload={
                "task_type": task_type,
                "title": title,
                "metadata": dict(metadata or {}),
            },
        )
        with self._lock:
            self._tasks[task_id] = record
        return record.to_state()

    def append_event(
        self,
        task_id: str,
        *,
        event_type: str,
        message: str,
        status: TaskStatus,
        payload: dict[str, Any] | None = None,
        progress: float | None = None,
        current_step: str | None = None,
        output: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> TaskEventData:
        record = self._get_record(task_id)
        with self._lock:
            return record.append_event(
                event_type,
                message=message,
                status=status,
                payload=payload,
                progress=progress,
                current_step=current_step,
                output=output,
                error=error,
            )

    def get_task(self, task_id: str) -> TaskStateData | None:
        record = self._get_record(task_id, required=False)
        if record is None:
            return None
        with self._lock:
            return record.to_state()

    def get_events(self, task_id: str) -> list[TaskEventData]:
        record = self._get_record(task_id, required=False)
        if record is None:
            return []
        with self._lock:
            return list(record.events)

    def clear(self) -> None:
        with self._lock:
            self._tasks.clear()

    def _get_record(self, task_id: str, *, required: bool = True) -> _TaskRecord | None:
        with self._lock:
            record = self._tasks.get(task_id)
        if record is None and required:
            raise KeyError(task_id)
        return record


class RedisTaskStore:
    def __init__(self, redis_url: str, prefix: str = "paiguangguang:tasks") -> None:
        if redis is None:  # pragma: no cover - optional dependency
            raise RuntimeError("redis package is not installed")
        self._client = redis.from_url(redis_url, decode_responses=True)
        self._prefix = prefix
        self._client.ping()

    def _task_key(self, task_id: str) -> str:
        return f"{self._prefix}:task:{task_id}"

    def _events_key(self, task_id: str) -> str:
        return f"{self._prefix}:task:{task_id}:events"

    def create_task(
        self,
        *,
        task_type: str,
        title: str,
        metadata: dict[str, Any] | None = None,
    ) -> TaskStateData:
        record = _TaskRecord(
            task_id=str(uuid4()),
            task_type=task_type,
            title=title,
            metadata=dict(metadata or {}),
        )
        record.append_event(
            "created",
            message="Task created",
            status="queued",
            payload={
                "task_type": task_type,
                "title": title,
                "metadata": dict(metadata or {}),
            },
        )
        self._client.set(self._task_key(record.task_id), json.dumps(record.to_state().model_dump(mode="json")))
        self._client.delete(self._events_key(record.task_id))
        self._client.rpush(
            self._events_key(record.task_id),
            *[json.dumps(event.model_dump(mode="json")) for event in record.events],
        )
        return record.to_state()

    def append_event(
        self,
        task_id: str,
        *,
        event_type: str,
        message: str,
        status: TaskStatus,
        payload: dict[str, Any] | None = None,
        progress: float | None = None,
        current_step: str | None = None,
        output: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> TaskEventData:
        state = self.get_task(task_id)
        if state is None:
            raise KeyError(task_id)

        events = self.get_events(task_id)
        sequence = len(events) + 1
        event = TaskEventData(
            event_id=f"{task_id}-{sequence}",
            sequence=sequence,
            task_id=task_id,
            event_type=event_type,  # type: ignore[arg-type]
            status=status,
            message=message,
            payload=payload or {},
            created_at=_now(),
        )
        events.append(event)

        state.status = status
        state.message = message
        if progress is not None:
            state.progress = progress
        if current_step is not None:
            state.current_step = current_step
        if output is not None:
            state.output = output
            state.progress = 1.0
        if error is not None:
            state.error = error
        if status in TERMINAL_STATUSES:
            state.completed_at = event.created_at
        state.updated_at = event.created_at
        state.event_count = len(events)
        state.latest_event = event

        self._client.set(self._task_key(task_id), json.dumps(state.model_dump(mode="json")))
        self._client.rpush(self._events_key(task_id), json.dumps(event.model_dump(mode="json")))
        return event

    def get_task(self, task_id: str) -> TaskStateData | None:
        payload = self._client.get(self._task_key(task_id))
        if not payload:
            return None
        return TaskStateData.model_validate(json.loads(payload))

    def get_events(self, task_id: str) -> list[TaskEventData]:
        payloads = self._client.lrange(self._events_key(task_id), 0, -1)
        return [TaskEventData.model_validate(json.loads(payload)) for payload in payloads]

    def clear(self) -> None:
        keys = self._client.keys(f"{self._prefix}:task:*")
        if keys:
            self._client.delete(*keys)


_IN_MEMORY_TASK_STORE = InMemoryTaskStore()
_REDIS_TASK_STORE: RedisTaskStore | None = None


def get_task_store() -> InMemoryTaskStore | RedisTaskStore:
    global _REDIS_TASK_STORE

    settings = get_settings()
    if settings.redis_url:
        if _REDIS_TASK_STORE is None:
            try:
                _REDIS_TASK_STORE = RedisTaskStore(settings.redis_url)
            except Exception:
                _REDIS_TASK_STORE = None
        if _REDIS_TASK_STORE is not None:
            return _REDIS_TASK_STORE
    return _IN_MEMORY_TASK_STORE
