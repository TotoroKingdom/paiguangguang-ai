from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SkillCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=1000)
    contentMd: str = Field(default="", max_length=100_000)


class SkillUpdate(SkillCreate):
    pass


class SkillView(BaseModel):
    id: str
    name: str
    description: str
    contentMd: str
    version: int
    createdAt: datetime
    updatedAt: datetime


class SkillListResponse(BaseModel):
    items: list[SkillView]


class FileView(BaseModel):
    id: str
    filename: str
    contentType: str
    sizeBytes: int
    checksum: str
    createdAt: datetime


class FileListResponse(BaseModel):
    items: list[FileView]


class McpServerCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=1000)
    endpointUrl: str = Field(min_length=8, max_length=512)
    transport: Literal["http", "sse"] = "http"


class McpServerView(BaseModel):
    id: str
    name: str
    description: str
    status: Literal["pending", "approved", "disabled"]
    transport: str
    tools: list[dict]
    createdAt: datetime
    reviewedAt: datetime | None = None


class McpServerListResponse(BaseModel):
    items: list[McpServerView]


class McpConnectionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    serverId: str = Field(min_length=1, max_length=36)
    token: str = Field(default="", max_length=4096)


class McpConnectionView(BaseModel):
    id: str
    serverId: str
    serverName: str
    status: str
    hasCredential: bool
    createdAt: datetime
    lastUsedAt: datetime | None = None


class McpConnectionListResponse(BaseModel):
    items: list[McpConnectionView]


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(default="", max_length=255)
