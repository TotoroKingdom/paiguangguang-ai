from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.chatbot.schemas.message import MessagePageData
from app.chatbot.services.message_service import MessageService, get_message_service
from app.db.session import get_db_session
from app.schemas.auth import AuthenticatedUserContextData
from app.schemas.common import ApiResponse
from app.services.auth import get_current_user_context

router = APIRouter(prefix="/conversations/{conversation_id}/messages", tags=["chatbot-messages"])


@router.get("", response_model=ApiResponse[MessagePageData])
def list_messages(
    conversation_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    before: str | None = Query(default=None),
    session: Session = Depends(get_db_session),
    current_user: AuthenticatedUserContextData = Depends(get_current_user_context),
    service: MessageService = Depends(get_message_service),
) -> ApiResponse[MessagePageData]:
    return ApiResponse(
        data=service.list_messages(
            session,
            current_user.id,
            conversation_id,
            limit=limit,
            before=before,
        )
    )

