from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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
