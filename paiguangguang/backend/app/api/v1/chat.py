from fastapi import APIRouter, Depends, HTTPException

from app.ai.deepseek import DeepSeekError
from app.schemas.chat import PortfolioChatData, PortfolioChatRequest
from app.schemas.common import ApiResponse
from app.services.portfolio_chat import (
    PortfolioChatService,
    get_portfolio_chat_service,
)

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@router.post("/chat", response_model=ApiResponse[PortfolioChatData])
def portfolio_chat(
    request: PortfolioChatRequest,
    service: PortfolioChatService = Depends(get_portfolio_chat_service),
) -> ApiResponse[PortfolioChatData]:
    try:
        result = service.reply(request)
    except (ValueError, DeepSeekError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return ApiResponse(data=result)
