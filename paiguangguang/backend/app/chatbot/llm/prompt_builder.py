from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from app.chatbot.llm.provider import ChatCompletionRequest, LLMMessage, coerce_message


@dataclass(frozen=True, slots=True)
class PromptBuilder:
    prompt_version: str
    system_prompt: str
    default_model: str = "deepseek-chat"

    def build_messages(
        self,
        *,
        user_message: str,
        history: Sequence[LLMMessage | Mapping[str, Any]] = (),
    ) -> tuple[LLMMessage, ...]:
        messages = [LLMMessage(role="system", content=self.system_prompt)]
        messages.extend(coerce_message(message) for message in history)
        messages.append(LLMMessage(role="user", content=user_message))
        return tuple(messages)

    def build_request(
        self,
        *,
        request_id: str,
        model: str | None = None,
        user_message: str,
        history: Sequence[LLMMessage | Mapping[str, Any]] = (),
        temperature: float | None = None,
        tools: Sequence[dict[str, Any]] = (),
        tool_choice: str | dict[str, Any] | None = None,
        max_tokens: int | None = None,
        top_p: float | None = None,
        extra: Mapping[str, Any] | None = None,
    ) -> ChatCompletionRequest:
        return ChatCompletionRequest(
            request_id=request_id,
            prompt_version=self.prompt_version,
            model=model or self.default_model,
            messages=self.build_messages(user_message=user_message, history=history),
            temperature=temperature,
            tools=tuple(dict(tool) for tool in tools),
            tool_choice=tool_choice,
            max_tokens=max_tokens,
            top_p=top_p,
            extra=dict(extra or {}),
        )
