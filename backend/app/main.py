from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import settings
from app.core.errors import APIError, api_error_handler
from app.db import SessionLocal, init_db
from app.modules.capabilities.router import admin_router as capability_admin_router
from app.modules.capabilities.router import creator_router as capability_creator_router
from app.modules.capabilities.router import governance_router as capability_governance_router
from app.modules.capabilities.router import public_router as capability_public_router
from app.modules.capabilities.service import CapabilityService
from app.modules.identity.router import router as admin_auth_router
from app.modules.identity.service import AdminIdentityService
from app.modules.identity.user_router import (
    admin_router as user_admin_router,
    auth_router,
    me_router,
)
from app.modules.identity.user_service import UserIdentityService
from app.modules.personal.router import (
    admin_router as mcp_admin_router,
    creator_router as mcp_creator_router,
    mcp_router,
    me_router as personal_me_router,
)
from app.modules.runtime.router import admin_router as runtime_admin_router
from app.modules.runtime.router import creator_router as runtime_creator_router
from app.modules.runtime.router import router as runtime_router
from app.routers import conversations

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    with SessionLocal() as session:
        AdminIdentityService(session).ensure_bootstrap_admin()
        UserIdentityService(session).ensure_unified_admin()
        if settings.demo_catalog_enabled:
            CapabilityService(session).ensure_demo_catalog()
        if (
            settings.environment.lower() in {"production", "prod"}
            and not AdminIdentityService(session).has_active_admin()
        ):
            raise RuntimeError(
                "No active administrator exists. Configure ASSISTANT_ADMIN_USERNAME "
                "and ASSISTANT_ADMIN_PASSWORD, or create one with app.admin_cli."
            )
        logger.info("Assistant database initialized")
    yield


app = FastAPI(
    title="Paiguangguang Assistant API",
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)
app.add_exception_handler(APIError, api_error_handler)
app.include_router(conversations.router, prefix="/api/v1")
app.include_router(admin_auth_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(me_router, prefix="/api/v1")
app.include_router(user_admin_router, prefix="/api/v1")
app.include_router(personal_me_router, prefix="/api/v1")
app.include_router(mcp_router, prefix="/api/v1")
app.include_router(mcp_admin_router, prefix="/api/v1")
app.include_router(mcp_creator_router, prefix="/api/v1")
app.include_router(runtime_router, prefix="/api/v1")
app.include_router(runtime_admin_router, prefix="/api/v1")
app.include_router(runtime_creator_router, prefix="/api/v1")
app.include_router(capability_public_router, prefix="/api/v1")
app.include_router(capability_admin_router, prefix="/api/v1")
app.include_router(capability_creator_router, prefix="/api/v1")
app.include_router(capability_governance_router, prefix="/api/v1")


@app.middleware("http")
async def request_guard(request: Request, call_next):
    if request.method in {"POST", "PATCH"} and request.url.path.startswith("/api/v1/"):
        content_type = request.headers.get("content-type", "").lower()
        is_file_upload = request.url.path == "/api/v1/me/files"
        if not content_type.startswith("application/json") and not (
            is_file_upload and content_type.startswith("multipart/form-data")
        ):
            return JSONResponse(status_code=415, content={"detail": "JSON request body required"})
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > settings.max_body_bytes:
        return JSONResponse(status_code=413, content={"detail": "Request body too large"})
    origin = request.headers.get("origin")
    if origin:
        normalized = origin.rstrip("/")
        same_origin = f"{request.url.scheme}://{request.headers.get('host', '')}".rstrip("/")
        if normalized not in settings.allowed_origin_values | {same_origin}:
            return JSONResponse(status_code=403, content={"detail": "Origin not allowed"})
    return await call_next(request)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
    )
    return response


@app.get("/api/v1/health")
def health_check() -> dict[str, str]:
    from app.db import engine

    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok", "service": settings.service_name}
