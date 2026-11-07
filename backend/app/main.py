from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import settings
from app.db import SessionLocal, init_db
from app.modules.capabilities.router import admin_router as capability_admin_router
from app.modules.capabilities.router import public_router as capability_public_router
from app.modules.capabilities.service import CapabilityService
from app.modules.identity.router import router as admin_auth_router
from app.modules.identity.service import AdminIdentityService
from app.routers import conversations

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    with SessionLocal() as session:
        AdminIdentityService(session).ensure_bootstrap_admin()
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
app.include_router(conversations.router, prefix="/api/v1")
app.include_router(admin_auth_router, prefix="/api/v1")
app.include_router(capability_public_router, prefix="/api/v1")
app.include_router(capability_admin_router, prefix="/api/v1")


@app.middleware("http")
async def request_guard(request: Request, call_next):
    if request.method in {"POST", "PATCH"} and request.url.path.startswith("/api/v1/"):
        content_type = request.headers.get("content-type", "").lower()
        if not content_type.startswith("application/json"):
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


@app.get("/api/v1/health")
def health_check() -> dict[str, str]:
    from app.db import engine

    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok", "service": settings.service_name}
