from __future__ import annotations

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import ExternalModelError, RetrievalFailureError, ServiceRateLimitError, ServiceTimeoutError
from app.db.bootstrap import initialize_database

logging.basicConfig(level=logging.INFO, format="%(message)s")

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

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
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
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
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": code,
                "message": detail,
            },
        },
    )


@app.exception_handler(ServiceTimeoutError)
async def service_timeout_handler(request: Request, exc: ServiceTimeoutError) -> JSONResponse:
    return JSONResponse(
        status_code=504,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": "TIMEOUT_ERROR",
                "message": exc.message,
            },
        },
    )


@app.exception_handler(ServiceRateLimitError)
async def service_rate_limit_handler(request: Request, exc: ServiceRateLimitError) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": "RATE_LIMITED",
                "message": exc.message,
            },
        },
    )


@app.exception_handler(RetrievalFailureError)
async def retrieval_failure_handler(request: Request, exc: RetrievalFailureError) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": "RETRIEVAL_ERROR",
                "message": exc.message,
            },
        },
    )


@app.exception_handler(ExternalModelError)
async def external_model_error_handler(request: Request, exc: ExternalModelError) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": "EXTERNAL_MODEL_ERROR",
                "message": exc.message,
            },
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    first_error = exc.errors()[0] if exc.errors() else None
    message = first_error["msg"] if first_error else "Invalid request"
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": message,
            },
        },
    )
