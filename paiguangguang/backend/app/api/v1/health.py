from fastapi import APIRouter

from app.schemas.common import ApiResponse, HealthData
from app.services.rag_cache import get_current_knowledge_base_version
from app.storage.cache import get_active_cache_backend
from app.core.config import get_settings

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health", response_model=ApiResponse[HealthData])
def health_check() -> ApiResponse[HealthData]:
    settings = get_settings()
    return ApiResponse(
        data=HealthData(
            status="ok",
            cache_backend=get_active_cache_backend(settings),
            knowledge_base_version=get_current_knowledge_base_version(settings.rag_collection_name),
        )
    )
