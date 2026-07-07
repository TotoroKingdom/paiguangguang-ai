from __future__ import annotations

from fastapi import APIRouter, Depends

from app.db.session import get_db_session
from app.schemas.auth import AuthTokenData, AuthenticatedUserContextData, LoginRequest, UserData
from app.schemas.common import ApiResponse
from app.services.auth import AuthService, get_auth_service, get_current_user_context

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=ApiResponse[AuthTokenData])
def login(
    request: LoginRequest,
    session=Depends(get_db_session),
    service: AuthService = Depends(get_auth_service),
) -> ApiResponse[AuthTokenData]:
    return ApiResponse(data=service.login(session, request))


@router.get("/me", response_model=ApiResponse[UserData])
def me(current_user: AuthenticatedUserContextData = Depends(get_current_user_context)) -> ApiResponse[UserData]:
    return ApiResponse(data=UserData.model_validate(current_user.model_dump()))
