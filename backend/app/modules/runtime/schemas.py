from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RunStepView(BaseModel):
    id: str
    seq: int
    type: str
    name: str
    status: str
    input: dict[str, Any]
    output: dict[str, Any]
    error: str
    durationMs: int


class RunTraceView(BaseModel):
    seq: int
    event: str
    detail: dict[str, Any]
    createdAt: datetime


class RunView(BaseModel):
    id: str
    status: str
    mode: str
    provider: str
    capabilityId: str
    versionId: str
    outputText: str
    errorCode: str
    errorMessage: str
    tokenInput: int
    tokenOutput: int
    stepCount: int
    createdAt: datetime
    startedAt: datetime | None
    finishedAt: datetime | None
    steps: list[RunStepView]
    traces: list[RunTraceView]


class RunListResponse(BaseModel):
    items: list[RunView]


class AdminRunView(BaseModel):
    id: str
    status: str
    mode: str
    provider: str
    capabilityId: str
    versionId: str
    errorCode: str
    stepCount: int
    createdAt: datetime
    startedAt: datetime | None
    finishedAt: datetime | None


class AdminRunListResponse(BaseModel):
    items: list[AdminRunView]


class CancelResponse(BaseModel):
    runId: str
    cancelRequested: bool = True


class RunQuotaResponse(BaseModel):
    limit: int
    used: int
    remaining: int
    resetsAt: str


class CreatorRunSummaryItem(BaseModel):
    id: str
    capabilityId: str
    capabilityName: str
    status: str
    mode: str
    createdAt: datetime


class CreatorRunSummaryResponse(BaseModel):
    total: int
    statuses: dict[str, int]
    recent: list[CreatorRunSummaryItem]


class ExecuteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversationId: str = Field(min_length=1, max_length=36)
    clientTurnId: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=1, max_length=6000)
    capabilityId: str | None = Field(default=None, max_length=36)
    capabilityKind: str | None = Field(default=None, max_length=16)
    toolArguments: dict[str, Any] = Field(default_factory=dict)
    # Deprecated compatibility field. Provider selection is server-controlled.
    mode: str | None = Field(default=None, max_length=16)


class RetryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversationId: str = Field(min_length=1, max_length=36)
    messageId: str = Field(min_length=1, max_length=36)
    # Deprecated compatibility field. Provider selection is server-controlled.
    mode: str | None = Field(default=None, max_length=16)
