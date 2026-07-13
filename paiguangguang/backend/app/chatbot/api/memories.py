from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.chatbot.schemas.common import DeleteResultData
from app.chatbot.schemas.memory import MemoryData, MemoryPageData, MemoryUpdateRequest
from app.chatbot.services.memory_service import MemoryService, get_memory_service
from app.db.session import get_db_session
from app.schemas.auth import AuthenticatedUserContextData
from app.schemas.common import ApiResponse
from app.services.auth import get_current_user_context

router = APIRouter(prefix="/memories", tags=["chatbot-memories"])


@router.get("", response_model=ApiResponse[MemoryPageData])
def list_memories(
    status: Literal["candidate", "active", "superseded"] = Query(default="active"),
    memory_type: str | None = Query(default=None),
    conversation_id: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    session: Session = Depends(get_db_session),
    current_user: AuthenticatedUserContextData = Depends(get_current_user_context),
    service: MemoryService = Depends(get_memory_service),
) -> ApiResponse[MemoryPageData]:
    return ApiResponse(
        data=service.list_memories(
            session,
            current_user.id,
            status=status,
            memory_type=memory_type,
            conversation_id=conversation_id,
            limit=limit,
            cursor=cursor,
        )
    )


@router.get("/{memory_id}", response_model=ApiResponse[MemoryData])
def get_memory(
    memory_id: str,
    session: Session = Depends(get_db_session),
    current_user: AuthenticatedUserContextData = Depends(get_current_user_context),
    service: MemoryService = Depends(get_memory_service),
) -> ApiResponse[MemoryData]:
    return ApiResponse(data=service.get_memory(session, current_user.id, memory_id))


@router.patch("/{memory_id}", response_model=ApiResponse[MemoryData])
def update_memory(
    memory_id: str,
    request: MemoryUpdateRequest,
    session: Session = Depends(get_db_session),
    current_user: AuthenticatedUserContextData = Depends(get_current_user_context),
    service: MemoryService = Depends(get_memory_service),
) -> ApiResponse[MemoryData]:
    return ApiResponse(data=service.update_memory(session, current_user.id, memory_id, request))


@router.delete("/{memory_id}", response_model=ApiResponse[DeleteResultData])
def delete_memory(
    memory_id: str,
    session: Session = Depends(get_db_session),
    current_user: AuthenticatedUserContextData = Depends(get_current_user_context),
    service: MemoryService = Depends(get_memory_service),
) -> ApiResponse[DeleteResultData]:
    return ApiResponse(data=service.delete_memory(session, current_user.id, memory_id))
