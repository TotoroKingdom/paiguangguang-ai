from fastapi import APIRouter, Depends, HTTPException

from app.ai.deepseek import DeepSeekError
from app.schemas.common import ApiResponse
from app.schemas.rag import (
    RagDocumentCreateRequest,
    RagDocumentData,
    RagIngestData,
    RagIngestRequest,
    RagIngestionJobData,
    RagQueryData,
    RagQueryRequest,
)
from app.services.rag_ingestion import RagIngestionService, get_rag_ingestion_service
from app.services.rag_query import RagQueryService, get_rag_query_service

router = APIRouter(prefix="/api/v1/rag", tags=["rag"])


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
    service: RagIngestionService = Depends(get_rag_ingestion_service),
) -> ApiResponse[RagIngestData]:
    try:
        result = service.ingest_document(request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Document {exc.args[0]} not found") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

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
    service: RagQueryService = Depends(get_rag_query_service),
) -> ApiResponse[RagQueryData]:
    try:
        result = service.query(request)
    except (ValueError, DeepSeekError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return ApiResponse(data=result)
