from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AdminLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)


class AdminUserView(BaseModel):
    id: str
    username: str
    role: Literal["admin", "viewer"]
    expiresAt: datetime


class AdminSessionResponse(BaseModel):
    authenticated: bool
    user: AdminUserView


UserRole = Literal["USER", "CREATOR", "ADMIN"]
UserStatus = Literal["PENDING", "ACTIVE", "DISABLED", "REJECTED"]
SessionScope = Literal["FULL", "STATUS_ONLY"]


class UserView(BaseModel):
    id: str
    accountNumber: str
    nickname: str
    role: UserRole
    status: UserStatus
    version: int
    createdAt: datetime
    activatedAt: datetime | None = None
    lastLoginAt: datetime | None = None


class RecoveryMaterial(BaseModel):
    code: str
    issuedAt: datetime
    displayMode: Literal["ONE_TIME"] = "ONE_TIME"


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password: str = Field(min_length=1, max_length=128)
    passwordConfirm: str = Field(min_length=1, max_length=128)
    nickname: str = Field(default="", max_length=80)

    @field_validator("nickname")
    @classmethod
    def trim_nickname(cls, value: str) -> str:
        return value.strip()


class RegisterResponse(BaseModel):
    user: UserView
    recovery: RecoveryMaterial | None = None
    sessionIssued: bool = False
    replayed: bool = False


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accountNumber: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=128)


class SessionInfo(BaseModel):
    scope: SessionScope
    expiresAt: datetime


class LoginResponse(BaseModel):
    authenticated: bool
    user: UserView
    session: SessionInfo


class SessionResponse(BaseModel):
    authenticated: bool
    user: UserView
    session: SessionInfo


class MeStatusResponse(BaseModel):
    user: UserView
    canUseService: bool


class LogoutResponse(BaseModel):
    loggedOut: bool = True


class RecoveryCompleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accountNumber: str = Field(min_length=1, max_length=32)
    recoveryCode: str = Field(min_length=8, max_length=256)
    newPassword: str = Field(min_length=1, max_length=128)
    newPasswordConfirm: str = Field(min_length=1, max_length=128)


class RecoveryCompleteResponse(BaseModel):
    ok: bool = True
    recovery: RecoveryMaterial
    sessionsRevoked: bool = True


class PasswordChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    currentPassword: str = Field(min_length=1, max_length=128)
    newPassword: str = Field(min_length=1, max_length=128)
    newPasswordConfirm: str = Field(min_length=1, max_length=128)


class RecoveryRotateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    currentPassword: str = Field(min_length=1, max_length=128)


class AdminUserListResponse(BaseModel):
    items: list[UserView]
    total: int
    nextCursor: str | None = None


class ModerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expectedVersion: int = Field(ge=1)
    reason: str = Field(default="", max_length=255)


class RoleUpdateRequest(ModerationRequest):
    role: UserRole


class ModerationResponse(BaseModel):
    user: UserView
    auditEventId: str


class ClaimLegacyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversationIds: list[str] = Field(default_factory=list, max_length=100)


class ClaimLegacyResponse(BaseModel):
    claimed: int
    skipped: int
    conversationIds: list[str]
