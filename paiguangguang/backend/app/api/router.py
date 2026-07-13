from fastapi import APIRouter

from app.chatbot.api.router import router as chatbot_router
from app.api.v1.auth import router as auth_router
from app.api.v1.admin import router as admin_router
from app.api.v1.browser import router as browser_router
from app.api.v1.chat import router as chat_router
from app.api.v1.health import router as health_router
from app.api.v1.office import router as office_router
from app.api.v1.rag import router as rag_router
from app.api.v1.tasks import router as tasks_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(admin_router)
api_router.include_router(browser_router)
api_router.include_router(chatbot_router)
# Legacy /api/v1/chat remains mounted during the deprecation window and returns 410.
api_router.include_router(chat_router)
api_router.include_router(office_router)
api_router.include_router(rag_router)
api_router.include_router(tasks_router)
api_router.include_router(health_router)
