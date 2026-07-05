from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.models import User
from app.db.session import get_db_session
from app.schemas.auth import AuthTokenData, LoginRequest, UserData

password_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


class AuthService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def hash_password(self, password: str) -> str:
        return password_context.hash(password)

    def verify_password(self, password: str, hashed_password: str) -> bool:
        return password_context.verify(password, hashed_password)

    def create_user(
        self,
        session: Session,
        *,
        email: str,
        display_name: str,
        password: str,
        is_active: bool = True,
    ) -> User:
        user = User(
            email=email.lower(),
            display_name=display_name,
            hashed_password=self.hash_password(password),
            is_active=is_active,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    def get_user_by_email(self, session: Session, email: str) -> User | None:
        statement = select(User).where(User.email == email.lower())
        return session.scalar(statement)

    def get_user_by_id(self, session: Session, user_id: str) -> User | None:
        statement = select(User).where(User.id == user_id)
        return session.scalar(statement)

    def authenticate_user(self, session: Session, email: str, password: str) -> User | None:
        user = self.get_user_by_email(session, email)
        if user is None or not user.is_active:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return user

    def create_access_token(self, user: User) -> str:
        if not self.settings.jwt_secret_key:
            raise ValueError("JWT_SECRET_KEY is required")

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=self.settings.jwt_access_token_expire_minutes)
        payload = {
            "sub": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
        }
        return jwt.encode(payload, self.settings.jwt_secret_key, algorithm=self.settings.jwt_algorithm)

    def decode_access_token(self, token: str) -> dict[str, object]:
        if not self.settings.jwt_secret_key:
            raise ValueError("JWT_SECRET_KEY is required")
        decoded = jwt.decode(
            token,
            self.settings.jwt_secret_key,
            algorithms=[self.settings.jwt_algorithm],
        )
        if not isinstance(decoded, dict):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
            )
        return decoded

    def login(self, session: Session, request: LoginRequest) -> AuthTokenData:
        user = self.authenticate_user(session, request.email, request.password)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        return AuthTokenData(access_token=self.create_access_token(user))

    def get_current_user(
        self,
        session: Session,
        credentials: HTTPAuthorizationCredentials | None,
    ) -> User:
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication credentials were not provided",
            )

        try:
            payload = self.decode_access_token(credentials.credentials)
        except jwt.PyJWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
            ) from exc

        subject = payload.get("sub")
        if not isinstance(subject, str) or not subject.strip():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
            )

        user = self.get_user_by_id(session, subject)
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
            )
        return user


_AUTH_SERVICE = AuthService()


def get_auth_service() -> AuthService:
    return _AUTH_SERVICE


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: Session = Depends(get_db_session),
    service: AuthService = Depends(get_auth_service),
) -> User:
    return service.get_current_user(session, credentials)


def user_to_data(user: User) -> UserData:
    return UserData(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )
