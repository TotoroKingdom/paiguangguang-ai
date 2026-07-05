from __future__ import annotations

from fastapi import APIRouter, Depends

from app.db.models import User
from app.db.session import get_db_session
from app.schemas.auth import AuthTokenData, LoginRequest, UserData
from app.schemas.common import ApiResponse
from app.services.auth import AuthService, get_auth_service, get_current_user, user_to_data

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=ApiResponse[AuthTokenData])
def login(
    request: LoginRequest,
    session=Depends(get_db_session),
    service: AuthService = Depends(get_auth_service),
) -> ApiResponse[AuthTokenData]:
    return ApiResponse(data=service.login(session, request))


@router.get("/me", response_model=ApiResponse[UserData])
def me(current_user: User = Depends(get_current_user)) -> ApiResponse[UserData]:
    return ApiResponse(data=user_to_data(current_user))
