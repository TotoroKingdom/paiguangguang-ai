from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class OfficeAgentRequest(BaseModel):
    workflow: str = Field(min_length=1, max_length=64)
    prompt: str = Field(min_length=1, max_length=4000)


class OfficeAgentStepData(BaseModel):
    step_id: str = Field(min_length=1)
    kind: Literal["plan", "tool_call", "observation", "synthesis"]
    title: str = Field(min_length=1)
    detail: str = Field(min_length=1)
    data: dict[str, Any] = Field(default_factory=dict)


class OfficeAgentFinalOutputData(BaseModel):
    artifact_type: Literal["summary", "report", "email"]
    title: str
    summary: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class OfficeAgentRunData(BaseModel):
    workflow: str
    prompt: str
    steps: list[OfficeAgentStepData]
    final_output: OfficeAgentFinalOutputData
