from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.common import ApiResponse
from app.schemas.task import TaskStateData
from app.services.task_service import TaskService, get_task_service

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


@router.get("/{task_id}", response_model=ApiResponse[TaskStateData])
def get_task_state(
    task_id: str,
    service: TaskService = Depends(get_task_service),
) -> ApiResponse[TaskStateData]:
    task = service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Unknown task: {task_id}")
    return ApiResponse(data=task)


@router.get("/{task_id}/events")
def stream_task_events(
    task_id: str,
    service: TaskService = Depends(get_task_service),
) -> StreamingResponse:
    task = service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Unknown task: {task_id}")

    def event_stream():
        for event in service.get_events(task_id):
            yield f"id: {event.sequence}\n"
            yield f"event: {event.event_type}\n"
            yield f"data: {json.dumps(event.model_dump(mode='json'), ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
