from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.chatbot.schemas.common import DeleteResultData
from app.chatbot.schemas.conversation import (
    ConversationCreateRequest,
    ConversationData,
    ConversationDetailData,
    ConversationPageData,
    ConversationUpdateRequest,
)
from app.chatbot.services.conversation_service import ConversationListStatus, ConversationService, get_conversation_service
from app.db.session import get_db_session
from app.schemas.auth import AuthenticatedUserContextData
from app.schemas.common import ApiResponse
from app.services.auth import get_current_user_context

router = APIRouter(prefix="/conversations", tags=["chatbot-conversations"])


@router.post("", response_model=ApiResponse[ConversationData], status_code=201)
def create_conversation(
    request: ConversationCreateRequest,
    session: Session = Depends(get_db_session),
    current_user: AuthenticatedUserContextData = Depends(get_current_user_context),
    service: ConversationService = Depends(get_conversation_service),
) -> ApiResponse[ConversationData]:
    return ApiResponse(data=service.create_conversation(session, current_user.id, request))


@router.get("", response_model=ApiResponse[ConversationPageData])
def list_conversations(
    status: ConversationListStatus = Query(default="active"),
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    session: Session = Depends(get_db_session),
    current_user: AuthenticatedUserContextData = Depends(get_current_user_context),
    service: ConversationService = Depends(get_conversation_service),
) -> ApiResponse[ConversationPageData]:
    return ApiResponse(data=service.list_conversations(session, current_user.id, status=status, limit=limit, cursor=cursor))


@router.get("/{conversation_id}", response_model=ApiResponse[ConversationDetailData])
def get_conversation(
    conversation_id: str,
    session: Session = Depends(get_db_session),
    current_user: AuthenticatedUserContextData = Depends(get_current_user_context),
    service: ConversationService = Depends(get_conversation_service),
) -> ApiResponse[ConversationDetailData]:
    return ApiResponse(data=service.get_conversation(session, current_user.id, conversation_id))


@router.patch("/{conversation_id}", response_model=ApiResponse[ConversationData])
def update_conversation(
    conversation_id: str,
    request: ConversationUpdateRequest,
    session: Session = Depends(get_db_session),
    current_user: AuthenticatedUserContextData = Depends(get_current_user_context),
    service: ConversationService = Depends(get_conversation_service),
) -> ApiResponse[ConversationData]:
    return ApiResponse(data=service.update_conversation(session, current_user.id, conversation_id, request))


@router.post("/{conversation_id}/archive", response_model=ApiResponse[ConversationData])
def archive_conversation(
    conversation_id: str,
    session: Session = Depends(get_db_session),
    current_user: AuthenticatedUserContextData = Depends(get_current_user_context),
    service: ConversationService = Depends(get_conversation_service),
) -> ApiResponse[ConversationData]:
    return ApiResponse(data=service.archive_conversation(session, current_user.id, conversation_id))


@router.post("/{conversation_id}/restore", response_model=ApiResponse[ConversationData])
def restore_conversation(
    conversation_id: str,
    session: Session = Depends(get_db_session),
    current_user: AuthenticatedUserContextData = Depends(get_current_user_context),
    service: ConversationService = Depends(get_conversation_service),
) -> ApiResponse[ConversationData]:
    return ApiResponse(data=service.restore_conversation(session, current_user.id, conversation_id))


@router.delete("/{conversation_id}", response_model=ApiResponse[DeleteResultData])
def delete_conversation(
    conversation_id: str,
    session: Session = Depends(get_db_session),
    current_user: AuthenticatedUserContextData = Depends(get_current_user_context),
    service: ConversationService = Depends(get_conversation_service),
) -> ApiResponse[DeleteResultData]:
    return ApiResponse(data=service.delete_conversation(session, current_user.id, conversation_id))

