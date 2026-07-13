from __future__ import annotations

from fastapi import APIRouter

from app.chatbot.api.conversations import router as conversations_router
from app.chatbot.api.memories import router as memories_router
from app.chatbot.api.messages import router as messages_router

router = APIRouter(prefix="/api/v1/chatbot", tags=["chatbot"])
router.include_router(conversations_router)
router.include_router(messages_router)
router.include_router(memories_router)
