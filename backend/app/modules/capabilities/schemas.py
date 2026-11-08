import json
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

CapabilityKind = Literal["tool", "skill", "mcp", "agent"]
CapabilityStatus = Literal["draft", "published", "disabled"]


class CapabilitySnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: CapabilityKind
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    category: str = Field(default="未分类", min_length=1, max_length=80)
    icon: str = Field(default="spark", min_length=1, max_length=48)
    steps: list[str] = Field(default_factory=list, max_length=30)
    tools: list[str] = Field(default_factory=list, max_length=30)
    content: str | None = Field(default=None, max_length=100_000)
    config: dict[str, Any] = Field(default_factory=dict)
    executionMode: Literal["demo", "simulated"] = "simulated"
    source: Literal["system", "managed"] = "managed"

    @field_validator("name", "category")
    @classmethod
    def trim_required(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be blank")
        return value

    @field_validator("steps")
    @classmethod
    def validate_steps(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values if value.strip()]
        if any(len(value) > 120 for value in cleaned):
            raise ValueError("steps must contain at most 120 characters each")
        return cleaned

    @field_validator("tools")
    @classmethod
    def validate_tools(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values if value.strip()]
        if any(len(value) > 120 for value in cleaned):
            raise ValueError("tools must contain at most 120 characters each")
        return cleaned

    @field_validator("config")
    @classmethod
    def validate_config(cls, value: dict[str, Any]) -> dict[str, Any]:
        encoded = json.dumps(value, ensure_ascii=False)
        if len(encoded.encode("utf-8")) > 24 * 1024:
            raise ValueError("config must be smaller than 24 KiB")
        return value


class CapabilityCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: CapabilityKind
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    category: str = Field(default="未分类", min_length=1, max_length=80)
    icon: str = Field(default="spark", min_length=1, max_length=48)
    steps: list[str] = Field(default_factory=list, max_length=30)
    tools: list[str] = Field(default_factory=list, max_length=30)
    content: str | None = Field(default=None, max_length=100_000)
    config: dict[str, Any] = Field(default_factory=dict)
    changelog: str = Field(default="", max_length=2000)


class CapabilityUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    draftVersionId: str | None = Field(default=None, max_length=36)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    category: str | None = Field(default=None, min_length=1, max_length=80)
    icon: str | None = Field(default=None, min_length=1, max_length=48)
    steps: list[str] | None = Field(default=None, max_length=30)
    tools: list[str] | None = Field(default=None, max_length=30)
    content: str | None = Field(default=None, max_length=100_000)
    config: dict[str, Any] | None = None
    changelog: str | None = Field(default=None, max_length=2000)


class PublishRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    versionId: str | None = Field(default=None, max_length=36)
    changelog: str = Field(default="", max_length=2000)


class CapabilityVersionView(BaseModel):
    id: str
    version: int
    status: Literal["draft", "published", "retired"]
    snapshot: CapabilitySnapshot
    changelog: str
    createdBy: str
    publishedBy: str
    createdAt: datetime
    publishedAt: datetime | None
    retiredAt: datetime | None


class CapabilitySummary(BaseModel):
    id: str
    slug: str
    kind: CapabilityKind
    name: str
    description: str
    category: str
    icon: str
    status: CapabilityStatus
    source: Literal["demo", "admin", "creator"]
    hasDraft: bool
    publishedVersion: int | None
    draftVersion: int | None
    executionMode: Literal["demo", "simulated"] | None
    visibility: Literal["platform", "private"] = "platform"
    accessMode: Literal["all_active", "granted"] = "all_active"
    reviewStatus: str = "none"
    ownerId: str | None = None
    testStatus: str = "untested"
    updatedAt: datetime


class CapabilityDetail(CapabilitySummary):
    createdAt: datetime
    createdBy: str
    draft: CapabilityVersionView | None
    published: CapabilityVersionView | None
    versions: list[CapabilityVersionView]


class CapabilityListResponse(BaseModel):
    items: list[CapabilitySummary]


class PublicCapability(BaseModel):
    id: str
    kind: CapabilityKind
    name: str
    description: str
    category: str
    icon: str
    source: Literal["system", "managed"]
    steps: list[str]
    tools: list[str]
    content: str | None
    executionMode: Literal["demo", "simulated"]
    visibility: Literal["platform", "private"] = "platform"
    accessMode: Literal["all_active", "granted"] = "all_active"
    authorized: bool = True
    ready: bool = False
    testStatus: str = "untested"
    version: int
    versionId: str


class PublicCapabilityListResponse(BaseModel):
    items: list[PublicCapability]


class ReleaseItem(BaseModel):
    capabilityId: str
    capabilityName: str
    kind: CapabilityKind
    versionId: str
    version: int
    status: Literal["published", "retired"]
    publishedBy: str
    publishedAt: datetime | None
    retiredAt: datetime | None


class ReleaseListResponse(BaseModel):
    items: list[ReleaseItem]


class RunItem(BaseModel):
    id: str
    capabilityId: str
    capabilityName: str
    kind: CapabilityKind | None
    version: int
    conversationId: str
    mode: str
    status: str
    createdAt: datetime


class RunListResponse(BaseModel):
    items: list[RunItem]
    total: int
    nextCursor: str | None


class AuditItem(BaseModel):
    id: str
    actorType: str
    actorId: str
    action: str
    resourceType: str
    resourceId: str
    detail: dict[str, Any]
    createdAt: datetime


class AuditListResponse(BaseModel):
    items: list[AuditItem]
    total: int
    nextCursor: str | None


class KindCount(BaseModel):
    kind: CapabilityKind
    total: int
    published: int
    draft: int
    disabled: int


class OverviewResponse(BaseModel):
    capabilities: list[KindCount]
    totalRuns: int
    recentRuns: list[RunItem]
    recentAudit: list[AuditItem]
    admin: dict[str, str]
    environment: str


class SettingsResponse(BaseModel):
    environment: str
    database: str
    adminSessionMinutes: int
    secureAdminCookie: bool
    allowedOrigins: list[str]
    loginRateLimit: dict[str, int]
    executionMode: str
    notes: list[str]


class ReviewActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(default="", max_length=255)


class GrantRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    userId: str = Field(min_length=1, max_length=36)


class ReviewEventView(BaseModel):
    id: str
    capabilityId: str
    versionId: str
    action: str
    actorId: str
    reason: str
    createdAt: datetime


class ReviewListResponse(BaseModel):
    items: list[ReviewEventView]
