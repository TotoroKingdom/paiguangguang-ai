from __future__ import annotations

from fastapi import Depends

from app.chatbot.errors import ChatbotApiError
from app.core.config import Settings, get_settings

from app.chatbot.services.cancellation_service import CancellationService, get_cancellation_service
from app.chatbot.services.concurrency_service import ConcurrencyService, get_concurrency_service
from app.chatbot.services.chat_service import ChatService, get_chat_service
from app.chatbot.services.recovery_service import RecoveryService, get_recovery_service
from app.chatbot.services.stream_service import ChatStreamService, get_chat_stream_service


def require_chatbot_enabled(settings: Settings = Depends(get_settings)) -> None:
    if not settings.chatbot_enabled:
        raise ChatbotApiError(
            status_code=503,
            code="CHATBOT_DISABLED",
            message="Chatbot is temporarily unavailable",
        )

__all__ = [
    "CancellationService",
    "ConcurrencyService",
    "ChatService",
    "ChatStreamService",
    "get_cancellation_service",
    "get_concurrency_service",
    "get_chat_service",
    "get_chat_stream_service",
    "RecoveryService",
    "get_recovery_service",
    "require_chatbot_enabled",
]
