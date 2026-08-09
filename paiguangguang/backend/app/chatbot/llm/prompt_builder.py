from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from app.chatbot.llm.provider import ChatCompletionRequest, LLMMessage, coerce_message


_UNTRUSTED_CONTEXT_START = "<<< untrusted {kind} context >>>"
_UNTRUSTED_CONTEXT_END = "<<< end untrusted context >>>"


def format_untrusted_context(*, kind: str, source_ids: Sequence[str], content: str) -> str:
    source_text = ",".join(str(source_id) for source_id in source_ids if str(source_id).strip()) or "unknown"
    return "\n".join(
        [
            _UNTRUSTED_CONTEXT_START.format(kind=kind),
            f"source_ids={source_text}",
            content,
            _UNTRUSTED_CONTEXT_END,
        ]
    )


@dataclass(frozen=True, slots=True)
class PromptBuilder:
    prompt_version: str
    system_prompt: str
    default_model: str = "deepseek-v4-flash"

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
