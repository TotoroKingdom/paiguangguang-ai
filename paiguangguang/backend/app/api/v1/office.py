from fastapi import APIRouter, Depends, HTTPException

from app.schemas.common import ApiResponse
from app.schemas.office import OfficeAgentRequest, OfficeAgentRunData
from app.services.office_agent import OfficeAgentService, get_office_agent_service

router = APIRouter(prefix="/api/v1/agents/office", tags=["agents"])


@router.post("/run", response_model=ApiResponse[OfficeAgentRunData])
def run_office_agent(
    request: OfficeAgentRequest,
    service: OfficeAgentService = Depends(get_office_agent_service),
) -> ApiResponse[OfficeAgentRunData]:
    try:
        result = service.run(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ApiResponse(data=result)
