from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class EncryptedLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    encrypted_password: str = Field(min_length=1, max_length=4096)
    key_id: str = Field(min_length=1, max_length=128)


class LoginEncryptionKeyData(BaseModel):
    key_id: str
    algorithm: str = "RSA-OAEP-256"
    public_key: dict[str, object]


class AuthTokenData(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserData(BaseModel):
    id: str
    email: str
    display_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AuthenticatedUserContextData(UserData):
    roles: list[str] = Field(default_factory=list)
    workspace_ids: list[str] = Field(default_factory=list)
    effective_permissions: list[str] = Field(default_factory=list)
