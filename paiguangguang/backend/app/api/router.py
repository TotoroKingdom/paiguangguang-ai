from fastapi import APIRouter

from app.api.v1.architecture import router as architecture_router
from app.api.v1.browser import router as browser_router
from app.api.v1.chat import router as chat_router
from app.api.v1.health import router as health_router
from app.api.v1.rag import router as rag_router

api_router = APIRouter()
api_router.include_router(architecture_router)
api_router.include_router(browser_router)
api_router.include_router(chat_router)
api_router.include_router(rag_router)
api_router.include_router(health_router)
