from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.chatbot.api.dependencies import get_cancellation_service
from app.chatbot.errors import ChatbotApiError
from app.chatbot.models.conversation import ChatbotConversation
from app.chatbot.models.llm_run import ChatbotLLMRun
from app.chatbot.models.message import ChatbotMessage
from app.chatbot.schemas.chat import ChatCompleteRequest
from app.chatbot.schemas.message import (
    GenerationRequest,
    MessagePageData,
    StopGenerationData,
    StopGenerationRequest,
)
from app.chatbot.schemas.stream import encode_chatbot_sse_event
from app.chatbot.services.cancellation_service import CancellationService
from app.chatbot.services.chat_service import ChatService, get_chat_service
from app.chatbot.services.message_service import MessageService, get_message_service
from app.chatbot.services.stream_service import ChatStreamService, get_chat_stream_service
from app.db.session import get_db_session
from app.schemas.auth import AuthenticatedUserContextData
from app.schemas.common import ApiResponse
from app.services.auth import get_current_user_context


router = APIRouter(prefix="/conversations/{conversation_id}", tags=["chatbot-messages"])


def _validate_idempotency_key(idempotency_key: str, client_request_id: UUID) -> str:
    try:
        normalized_header = str(UUID(idempotency_key))
    except Exception as exc:  # pragma: no cover - defensive
        raise ChatbotApiError(
            status_code=422,
            code="VALIDATION_ERROR",
            message="Idempotency-Key must be a UUID",
        ) from exc

    if normalized_header != str(client_request_id):
        raise ChatbotApiError(
            status_code=400,
            code="CHATBOT_IDEMPOTENCY_KEY_MISMATCH",
            message="Idempotency-Key must match client_request_id",
        )
    return normalized_header


@router.get("/messages", response_model=ApiResponse[MessagePageData])
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


@router.post("/messages", response_class=StreamingResponse)
def send_message(
    conversation_id: str,
    request: ChatCompleteRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    current_user: AuthenticatedUserContextData = Depends(get_current_user_context),
    service: ChatStreamService = Depends(get_chat_stream_service),
) -> StreamingResponse:
    _validate_idempotency_key(idempotency_key, request.client_request_id)
    stream = service.stream_completion(current_user.id, conversation_id, request.content, str(request.client_request_id))
    def event_iter():
        for item in stream:
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


@router.post("/messages/{message_id}/retry", response_class=StreamingResponse)
def retry_message(
    conversation_id: str,
    message_id: str,
    request: GenerationRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    current_user: AuthenticatedUserContextData = Depends(get_current_user_context),
    service: ChatStreamService = Depends(get_chat_stream_service),
) -> StreamingResponse:
    _validate_idempotency_key(idempotency_key, request.client_request_id)
    stream = service.stream_retry(current_user.id, conversation_id, message_id, str(request.client_request_id))
    def event_iter():
        for item in stream:
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


@router.post("/messages/{message_id}/regenerate", response_class=StreamingResponse)
def regenerate_message(
    conversation_id: str,
    message_id: str,
    request: GenerationRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    current_user: AuthenticatedUserContextData = Depends(get_current_user_context),
    service: ChatStreamService = Depends(get_chat_stream_service),
) -> StreamingResponse:
    _validate_idempotency_key(idempotency_key, request.client_request_id)
    stream = service.stream_regenerate(current_user.id, conversation_id, message_id, str(request.client_request_id))
    def event_iter():
        for item in stream:
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


@router.post("/stop", response_model=ApiResponse[StopGenerationData])
def stop_generation(
    conversation_id: str,
    request: StopGenerationRequest,
    session: Session = Depends(get_db_session),
    current_user: AuthenticatedUserContextData = Depends(get_current_user_context),
    chat_service: ChatService = Depends(get_chat_service),
    cancellation_service: CancellationService = Depends(get_cancellation_service),
) -> JSONResponse:
    conversation = session.scalar(
        select(ChatbotConversation).where(
            ChatbotConversation.id == conversation_id,
            ChatbotConversation.user_id == current_user.id,
            ChatbotConversation.deleted_at.is_(None),
        )
    )
    if conversation is None:
        raise ChatbotApiError(
            status_code=404,
            code="CHATBOT_CONVERSATION_NOT_FOUND",
            message="Conversation not found",
        )

    assistant_message: ChatbotMessage | None = None
    llm_run: ChatbotLLMRun | None = None
    if request.assistant_message_id is not None:
        _, assistant_message, llm_run = chat_service._load_turn_by_assistant_message_id(
            session,
            current_user.id,
            conversation_id,
            str(request.assistant_message_id),
        )
    else:
        llm_run = session.scalar(
            select(ChatbotLLMRun)
            .where(
                ChatbotLLMRun.conversation_id == conversation_id,
                ChatbotLLMRun.user_id == current_user.id,
                ChatbotLLMRun.status.in_(("pending", "streaming")),
            )
            .order_by(ChatbotLLMRun.updated_at.desc(), ChatbotLLMRun.id.desc())
            .limit(1)
        )
        if llm_run is None:
            raise ChatbotApiError(
                status_code=409,
                code="CHATBOT_NO_ACTIVE_GENERATION",
                message="Conversation has no active generation",
            )
        assistant_message = session.get(ChatbotMessage, llm_run.message_id)
        if assistant_message is None:
            raise ChatbotApiError(
                status_code=500,
                code="CHATBOT_CHAT_STATE_CORRUPTED",
                message="Chat state is inconsistent",
            )

    if llm_run is None:
        llm_run = session.scalar(
            select(ChatbotLLMRun)
            .where(
                ChatbotLLMRun.message_id == assistant_message.id,
                ChatbotLLMRun.user_id == current_user.id,
                ChatbotLLMRun.conversation_id == conversation_id,
            )
            .limit(1)
        )
        if llm_run is None:
            raise ChatbotApiError(
                status_code=500,
                code="CHATBOT_CHAT_STATE_CORRUPTED",
                message="Chat state is inconsistent",
            )

    if assistant_message.status == "cancelled" and llm_run.status == "cancelled":
        payload = ApiResponse(
            data=StopGenerationData(
                conversation_id=UUID(conversation_id),
                assistant_message_id=UUID(assistant_message.id),
                status="cancelled",
            )
        )
        return JSONResponse(content=payload.model_dump(mode="json"))

    if assistant_message.status in {"completed", "failed"} and llm_run.status in {"completed", "failed"}:
        payload = ApiResponse(
            data=StopGenerationData(
                conversation_id=UUID(conversation_id),
                assistant_message_id=UUID(assistant_message.id),
                status="already_terminal",
            )
        )
        return JSONResponse(content=payload.model_dump(mode="json"))

    cancellation_service.request_stop(conversation_id, assistant_message.id)
    payload = ApiResponse(
        data=StopGenerationData(
            conversation_id=UUID(conversation_id),
            assistant_message_id=UUID(assistant_message.id),
            status="cancellation_requested",
        )
    )
    return JSONResponse(content=payload.model_dump(mode="json"), status_code=202)
