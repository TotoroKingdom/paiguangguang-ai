from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.config import get_settings
from app.core.rate_limit import RateLimitConfig, get_rate_limiter
from app.schemas.common import ApiResponse
from app.db.session import get_db_session
from app.schemas.rag import (
    RagDocumentCreateRequest,
    RagDocumentData,
    RagIngestData,
    RagIngestRequest,
    RagIngestionJobData,
    RagQueryData,
    RagQueryRequest,
)
from app.services.auth import get_current_user
from app.services.rag_ingestion import RagIngestionService, get_rag_ingestion_service
from app.services.rag_query import RagQueryService, get_rag_query_service
from app.services.rbac import RBACService, get_rbac_service

router = APIRouter(prefix="/api/v1/rag", tags=["rag"])


def _apply_rate_limit(operation: str, key: str) -> None:
    settings = get_settings()
    get_rate_limiter().check(
        key,
        RateLimitConfig(
            max_requests=settings.rag_rate_limit_max_requests,
            window_seconds=settings.rag_rate_limit_window_seconds,
        ),
        operation=operation,
    )


@router.post("/documents", response_model=ApiResponse[RagDocumentData])
def register_document(
    request: RagDocumentCreateRequest,
    service: RagIngestionService = Depends(get_rag_ingestion_service),
) -> ApiResponse[RagDocumentData]:
    result = service.register_document(request)
    return ApiResponse(data=result)


@router.get("/documents/{document_id}", response_model=ApiResponse[RagDocumentData])
def get_document(
    document_id: str,
    service: RagIngestionService = Depends(get_rag_ingestion_service),
) -> ApiResponse[RagDocumentData]:
    try:
        result = service.get_document(document_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Document {exc.args[0]} not found") from exc
    return ApiResponse(data=result)


@router.post("/ingest", response_model=ApiResponse[RagIngestData])
def ingest_document(
    request: RagIngestRequest,
    http_request: Request,
    service: RagIngestionService = Depends(get_rag_ingestion_service),
) -> ApiResponse[RagIngestData]:
    client_host = http_request.client.host if http_request.client is not None else "unknown"
    _apply_rate_limit("Document ingestion", f"rag:ingest:{client_host}")
    try:
        result = service.ingest_document(request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Document {exc.args[0]} not found") from exc

    return ApiResponse(data=result)


@router.get("/ingestion-jobs/{job_id}", response_model=ApiResponse[RagIngestionJobData])
def get_ingestion_job(
    job_id: str,
    service: RagIngestionService = Depends(get_rag_ingestion_service),
) -> ApiResponse[RagIngestionJobData]:
    try:
        result = service.get_ingestion_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Job {exc.args[0]} not found") from exc
    return ApiResponse(data=result)


@router.post("/query", response_model=ApiResponse[RagQueryData])
def query_knowledge(
    request: RagQueryRequest,
    http_request: Request,
    service: RagQueryService = Depends(get_rag_query_service),
    session = Depends(get_db_session),
    current_user = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> ApiResponse[RagQueryData]:
    del http_request
    _apply_rate_limit("RAG query", f"rag:query:{current_user.id}")
    result = service.query_for_user(
        request,
        session=session,
        user=current_user,
        rbac_service=rbac_service,
    )

    return ApiResponse(data=result)
