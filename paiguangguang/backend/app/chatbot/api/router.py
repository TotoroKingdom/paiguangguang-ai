from __future__ import annotations

from fastapi import APIRouter

from app.chatbot.api.conversations import router as conversations_router

router = APIRouter(prefix="/api/v1/chatbot", tags=["chatbot"])
router.include_router(conversations_router)

