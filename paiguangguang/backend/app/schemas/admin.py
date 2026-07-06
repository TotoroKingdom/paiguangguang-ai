from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

from app.schemas.rag import RagDocumentData, RagIngestionJobData

DataT = TypeVar("DataT")


class AdminPagedData(BaseModel, Generic[DataT]):
    items: list[DataT]
    total: int
    page: int
    page_size: int


class AdminUserCreateRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    display_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=1, max_length=256)
    is_active: bool = True
    roles: list[str] = Field(default_factory=list)
    workspace_slugs: list[str] = Field(default_factory=list)


class AdminUserUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    password: str | None = Field(default=None, min_length=1, max_length=256)
    is_active: bool | None = None
    roles: list[str] | None = None
    workspace_slugs: list[str] | None = None


class AdminUserData(BaseModel):
    id: str
    email: str
    display_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    roles: list[str] = Field(default_factory=list)
    workspace_ids: list[str] = Field(default_factory=list)
    effective_permissions: list[str] = Field(default_factory=list)


class AdminRoleCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    permissions: list[str] = Field(default_factory=list)


class AdminRoleUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    permissions: list[str] | None = None


class AdminRoleData(BaseModel):
    id: str
    name: str
    description: str | None
    permissions: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class AdminPermissionCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)


class AdminPermissionUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)


class AdminPermissionData(BaseModel):
    id: str
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class AdminWorkspaceCreateRequest(BaseModel):
    slug: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    is_default: bool = False


class AdminWorkspaceUpdateRequest(BaseModel):
    slug: str | None = Field(default=None, min_length=1, max_length=100)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    is_default: bool | None = None


class AdminWorkspaceData(BaseModel):
    id: str
    slug: str
    name: str
    is_default: bool
    created_at: datetime
    updated_at: datetime


class AdminDocumentCreateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    original_filename: str | None = Field(default=None, max_length=255)
    text: str = Field(min_length=1, max_length=200_000)
    owner_user_id: str | None = Field(default=None, max_length=36)
    workspace_id: str | None = Field(default=None, max_length=36)
    permission_scope: str | None = Field(default=None, max_length=100)


class AdminDocumentUpdateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    original_filename: str | None = Field(default=None, max_length=255)
    text: str | None = Field(default=None, min_length=1, max_length=200_000)
    owner_user_id: str | None = Field(default=None, max_length=36)
    workspace_id: str | None = Field(default=None, max_length=36)
    permission_scope: str | None = Field(default=None, max_length=100)
    status: str | None = Field(default=None, max_length=50)
    parse_status: str | None = Field(default=None, max_length=50)
    chunk_status: str | None = Field(default=None, max_length=50)
    embedding_status: str | None = Field(default=None, max_length=50)
    index_status: str | None = Field(default=None, max_length=50)
    error_message: str | None = None
    is_deleted: bool | None = None


class AdminIngestionJobUpdateRequest(BaseModel):
    status: str | None = Field(default=None, max_length=50)
    failure_reason: str | None = None
    retry_count: int | None = Field(default=None, ge=0)
    is_reindex: bool | None = None
    chunk_size: int | None = Field(default=None, ge=1, le=4000)
    chunk_overlap: int | None = Field(default=None, ge=0, le=1000)


AdminDocumentData = RagDocumentData
AdminIngestionJobData = RagIngestionJobData
