from fastapi import APIRouter, Depends

from app.schemas.browser import BrowserAgentRequest, BrowserAgentRunData
from app.schemas.common import ApiResponse
from app.services.browser_agent import BrowserAgentService, get_browser_agent_service

router = APIRouter(prefix="/api/v1/agents/browser", tags=["agents"])


@router.post("/run", response_model=ApiResponse[BrowserAgentRunData])
def run_browser_agent(
    request: BrowserAgentRequest,
    service: BrowserAgentService = Depends(get_browser_agent_service),
) -> ApiResponse[BrowserAgentRunData]:
    result = service.run(request)
    return ApiResponse(data=result)
