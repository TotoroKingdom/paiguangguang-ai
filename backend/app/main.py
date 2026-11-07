from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import settings
from app.db import init_db
from app.routers import conversations


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Paiguangguang Assistant API",
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)
app.include_router(conversations.router, prefix="/api/v1")


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
