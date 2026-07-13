from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.chatbot.errors import ChatbotApiError
from app.chatbot.schemas.chat import ChatCompleteRequest
from app.chatbot.schemas.stream import encode_chatbot_sse_event
from app.chatbot.schemas.message import MessagePageData
from app.chatbot.services.message_service import MessageService, get_message_service
from app.chatbot.services.stream_service import ChatStreamService, get_chat_stream_service
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


@router.post("", response_class=StreamingResponse)
def send_message(
    conversation_id: str,
    request: ChatCompleteRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    current_user: AuthenticatedUserContextData = Depends(get_current_user_context),
    service: ChatStreamService = Depends(get_chat_stream_service),
) -> StreamingResponse:
    try:
        normalized_header = str(UUID(idempotency_key))
    except Exception as exc:  # pragma: no cover - defensive
        raise ChatbotApiError(
            status_code=422,
            code="VALIDATION_ERROR",
            message="Idempotency-Key must be a UUID",
        ) from exc

    if normalized_header != str(request.client_request_id):
        raise ChatbotApiError(
            status_code=400,
            code="CHATBOT_IDEMPOTENCY_KEY_MISMATCH",
            message="Idempotency-Key must match client_request_id",
        )

    def event_iter():
        for item in service.stream_completion(current_user.id, conversation_id, request.content, str(request.client_request_id)):
            if isinstance(item, str):
                yield item
            else:
                yield encode_chatbot_sse_event(item)

    return StreamingResponse(
        event_iter(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
