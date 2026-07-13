from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, Sequence, runtime_checkable


@dataclass(frozen=True, slots=True)
class LLMMessage:
    role: str
    content: str
    name: str | None = None

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.name is not None:
            payload["name"] = self.name
        return payload


@dataclass(frozen=True, slots=True)
class ChatCompletionUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass(frozen=True, slots=True)
class ChatCompletionRequest:
    request_id: str
    prompt_version: str
    model: str
    messages: tuple[LLMMessage, ...]
    temperature: float | None = None
    tools: tuple[dict[str, Any], ...] = ()
    tool_choice: str | dict[str, Any] | None = None
    max_tokens: int | None = None
    top_p: float | None = None
    extra: Mapping[str, Any] = field(default_factory=dict)

    def to_payload(self, *, stream: bool) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [message.to_payload() for message in self.messages],
            "stream": stream,
        }
        if self.temperature is not None:
            payload["temperature"] = self.temperature
        if self.tools:
            payload["tools"] = [dict(tool) for tool in self.tools]
        if self.tool_choice is not None:
            payload["tool_choice"] = self.tool_choice
        if self.max_tokens is not None:
            payload["max_tokens"] = self.max_tokens
        if self.top_p is not None:
            payload["top_p"] = self.top_p
        if self.extra:
            payload.update(dict(self.extra))
        return payload


@dataclass(frozen=True, slots=True)
class ChatCompletionResult:
    request_id: str
    prompt_version: str
    model: str
    message: LLMMessage
    finish_reason: str | None = None
    usage: ChatCompletionUsage | None = None
    raw_response: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class LLMStreamEvent:
    kind: str
    request_id: str
    prompt_version: str
    model: str
    content: str | None = None
    usage: ChatCompletionUsage | None = None
    finish_reason: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    raw_response: Mapping[str, Any] | None = None


@runtime_checkable
class LLMProvider(Protocol):
    def complete(self, request: ChatCompletionRequest) -> ChatCompletionResult:
        ...

    def stream(self, request: ChatCompletionRequest):
        ...

    def close(self) -> None:
        ...


def coerce_message(message: LLMMessage | Mapping[str, Any]) -> LLMMessage:
    if isinstance(message, LLMMessage):
        return message
    role = message.get("role")
    content = message.get("content")
    name = message.get("name")
    if not isinstance(role, str):
        raise TypeError("LLM message role must be a string")
    if not isinstance(content, str):
        raise TypeError("LLM message content must be a string")
    if name is not None and not isinstance(name, str):
        raise TypeError("LLM message name must be a string when provided")
    return LLMMessage(role=role, content=content, name=name)
