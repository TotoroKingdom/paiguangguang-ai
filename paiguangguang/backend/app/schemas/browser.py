from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class BrowserAgentRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=3, ge=1, le=5)


class BrowserSearchResultData(BaseModel):
    title: str
    url: str
    snippet: str
    score: float


class BrowserAgentStepData(BaseModel):
    step_id: str
    kind: Literal["plan", "tool_call", "observation", "synthesis"]
    title: str
    detail: str
    data: dict[str, Any] = Field(default_factory=dict)


class BrowserAgentRunData(BaseModel):
    prompt: str
    search_query: str
    steps: list[BrowserAgentStepData]
    search_results: list[BrowserSearchResultData]
    final_answer: str
