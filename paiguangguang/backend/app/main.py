from __future__ import annotations

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import (
    ExternalModelError,
    RetrievalFailureError,
    ServiceRateLimitError,
    ServiceTimeoutError,
    build_error_response,
)
from app.chatbot.errors import ChatbotApiError
from app.chatbot.observability import log_chatbot_event
from app.core.request_id import RequestIdMiddleware
from app.core.request_id import get_request_id
from app.db.bootstrap import initialize_database
from app.chatbot.services.runtime import build_chatbot_runtime

logging.basicConfig(level=logging.INFO, format="%(message)s")

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    runtime = build_chatbot_runtime()
    await runtime.start()
    try:
        yield
    finally:
        await runtime.stop()


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Paiguangguang backend is running"}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, str) else "Request failed"
    code = "HTTP_ERROR"
    if exc.status_code == 401:
        code = "AUTHENTICATION_ERROR"
    elif exc.status_code == 403:
        code = "PERMISSION_DENIED"
    elif exc.status_code == 429:
        code = "RATE_LIMITED"
    elif exc.status_code in {408, 504}:
        code = "TIMEOUT_ERROR"
    elif exc.status_code == 502:
        code = "EXTERNAL_MODEL_ERROR"
    return build_error_response(
        status_code=exc.status_code,
        code=code,
        message=detail,
        details=exc.detail if not isinstance(exc.detail, str) else None,
    )


@app.exception_handler(ChatbotApiError)
async def chatbot_api_error_handler(request: Request, exc: ChatbotApiError):
    log_chatbot_event(
        "chatbot.error",
        request_id=get_request_id(),
        status=exc.status_code,
        error_code=exc.code,
        reason=exc.__class__.__name__,
        extra={
            "path": request.url.path,
            "method": request.method,
        },
    )
    return build_error_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
    )


@app.exception_handler(ServiceTimeoutError)
async def service_timeout_handler(request: Request, exc: ServiceTimeoutError):
    return build_error_response(
        status_code=504,
        code="TIMEOUT_ERROR",
        message=exc.message,
    )


@app.exception_handler(ServiceRateLimitError)
async def service_rate_limit_handler(request: Request, exc: ServiceRateLimitError):
    return build_error_response(
        status_code=429,
        code="RATE_LIMITED",
        message=exc.message,
    )


@app.exception_handler(RetrievalFailureError)
async def retrieval_failure_handler(request: Request, exc: RetrievalFailureError):
    return build_error_response(
        status_code=502,
        code="RETRIEVAL_ERROR",
        message=exc.message,
    )


@app.exception_handler(ExternalModelError)
async def external_model_error_handler(request: Request, exc: ExternalModelError):
    return build_error_response(
        status_code=502,
        code="EXTERNAL_MODEL_ERROR",
        message=exc.message,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    first_error = exc.errors()[0] if exc.errors() else None
    message = first_error["msg"] if first_error else "Invalid request"
    return build_error_response(
        status_code=422,
        code="VALIDATION_ERROR",
        message=message,
        details=exc.errors(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logging.exception("Unhandled application error", exc_info=exc)
    return build_error_response(
        status_code=500,
        code="INTERNAL_ERROR",
        message="Internal server error",
    )
