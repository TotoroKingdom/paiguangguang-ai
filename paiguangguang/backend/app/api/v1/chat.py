from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.chatbot.observability import log_chatbot_event
from app.core.errors import build_error_response
from app.schemas.auth import AuthenticatedUserContextData
from app.services.auth import get_current_user_context

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@router.post("/chat", response_class=JSONResponse)
def portfolio_chat(
    current_user: AuthenticatedUserContextData = Depends(get_current_user_context),
) -> JSONResponse:
    log_chatbot_event(
        "chatbot.legacy_chat.deprecated",
        user_id=current_user.id,
        status="deprecated",
        source="compatibility_layer",
    )
    return build_error_response(
        status_code=410,
        code="CHATBOT_LEGACY_CHAT_DEPRECATED",
        message="Legacy chat endpoint has moved to /api/v1/chatbot",
        details={"new_base_path": "/api/v1/chatbot"},
        headers={
            "Deprecation": "true",
            "Sunset": "Tue, 30 Sep 2025 00:00:00 GMT",
            "Link": '</api/v1/chatbot>; rel="alternate"',
        },
    )
