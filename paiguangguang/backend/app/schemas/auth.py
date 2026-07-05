from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=256)


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
