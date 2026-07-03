from fastapi import APIRouter, Depends

from app.schemas.architecture import ArchitectureGraphData
from app.schemas.common import ApiResponse
from app.services.architecture_graph import (
    ArchitectureGraphService,
    get_architecture_graph_service,
)

router = APIRouter(prefix="/api/v1/architecture", tags=["architecture"])


@router.get("/graphs/system", response_model=ApiResponse[ArchitectureGraphData])
def get_system_graph(
    service: ArchitectureGraphService = Depends(get_architecture_graph_service),
) -> ApiResponse[ArchitectureGraphData]:
    return ApiResponse(data=service.get_system_graph())
