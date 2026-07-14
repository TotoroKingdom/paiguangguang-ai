from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.db.session import get_db_session
from app.schemas.auth import (
    AuthTokenData,
    AuthenticatedUserContextData,
    EncryptedLoginRequest,
    LoginEncryptionKeyData,
    UserData,
)
from app.schemas.common import ApiResponse
from app.services.auth import AuthService, get_auth_service, get_current_user_context
from app.services.login_encryption import (
    InvalidLoginEnvelope,
    LoginEncryptionService,
    get_login_encryption_service,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/encryption-key", response_model=ApiResponse[LoginEncryptionKeyData])
def encryption_key(
    encryption_service: LoginEncryptionService = Depends(get_login_encryption_service),
) -> ApiResponse[LoginEncryptionKeyData]:
    return ApiResponse(data=encryption_service.get_public_key_data())


@router.post("/login", response_model=ApiResponse[AuthTokenData])
def login(
    request: EncryptedLoginRequest,
    session=Depends(get_db_session),
    service: AuthService = Depends(get_auth_service),
    encryption_service: LoginEncryptionService = Depends(get_login_encryption_service),
) -> ApiResponse[AuthTokenData]:
    try:
        password = encryption_service.decrypt_password(request)
    except InvalidLoginEnvelope as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        ) from exc
    return ApiResponse(data=service.login_with_password(session, request.email, password))


@router.get("/me", response_model=ApiResponse[UserData])
def me(current_user: AuthenticatedUserContextData = Depends(get_current_user_context)) -> ApiResponse[UserData]:
    return ApiResponse(data=UserData.model_validate(current_user.model_dump()))
