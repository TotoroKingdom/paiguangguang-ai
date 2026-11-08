import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import settings
from app.core.errors import APIError


@dataclass
class LLMChunk:
    text: str = ""
    done: bool = False
    token_input: int = 0
    token_output: int = 0


class FakeProvider:
    name = "fake"

    async def stream(
        self, messages: list[dict[str, str]], *, tools: list[dict[str, Any]] | None = None
    ) -> AsyncIterator[LLMChunk]:
        user_text = next(
            (item["content"] for item in reversed(messages) if item["role"] == "user"), ""
        )
        tool_context = next(
            (item["content"] for item in reversed(messages) if item["role"] == "tool"), ""
        )
        system_context = next(
            (item["content"].splitlines()[0] for item in messages if item["role"] == "system"),
            "",
        )
        if tool_context:
            reply = f"[FakeProvider] 已调用只读工具，结果：{tool_context[:500]}"
        elif system_context:
            reply = (
                f"[FakeProvider] 已加载{system_context[:80]}。已收到：{user_text[:200]}。"
                "当前为测试提供方，未调用真实模型。"
            )
        else:
            reply = f"[FakeProvider] 已收到：{user_text[:200]}。当前为测试提供方，未调用真实模型。"
        for index in range(0, len(reply), 8):
            await asyncio.sleep(0)
            yield LLMChunk(text=reply[index : index + 8])
        yield LLMChunk(
            done=True,
            token_input=max(1, len(user_text) // 4),
            token_output=max(1, len(reply) // 4),
        )


class OpenAICompatibleProvider:
    name = "openai-compatible"

    def __init__(self) -> None:
        if not settings.llm_base_url or not settings.llm_model or settings.llm_api_key is None:
            raise APIError(
                503,
                "REAL_PROVIDER_NOT_CONFIGURED",
                "真实模型未配置，已拒绝执行",
            )

    async def stream(
        self, messages: list[dict[str, str]], *, tools: list[dict[str, Any]] | None = None
    ) -> AsyncIterator[LLMChunk]:
        url = settings.llm_base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.llm_api_key.get_secret_value()}",
            "Content-Type": "application/json",
        }
        body: dict[str, Any] = {
            "model": settings.llm_model,
            "messages": messages,
            "stream": True,
        }
        if tools:
            body["tools"] = tools
        timeout = httpx.Timeout(settings.llm_timeout_seconds)
        completed = False
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream("POST", url, headers=headers, json=body) as response:
                    if response.status_code >= 400:
                        raise APIError(502, "LLM_UPSTREAM_ERROR", "模型服务返回错误")
                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        payload = line[5:].strip()
                        if payload == "[DONE]":
                            completed = True
                            break
                        try:
                            data = json.loads(payload)
                        except json.JSONDecodeError:
                            continue
                        choice = (data.get("choices") or [{}])[0]
                        delta = choice.get("delta") or {}
                        text = delta.get("content") or ""
                        if text:
                            yield LLMChunk(text=text)
        except httpx.TimeoutException as error:
            raise APIError(504, "LLM_TIMEOUT", "模型请求超时") from error
        except httpx.HTTPError as error:
            raise APIError(503, "LLM_UNAVAILABLE", "模型服务不可达") from error
        if not completed:
            raise APIError(502, "LLM_STREAM_TRUNCATED", "模型流提前中断")
        yield LLMChunk(done=True)


def build_provider(mode: str | None = None):
    selected = (mode or settings.llm_provider or "fake").lower()
    if selected in {"fake", "test"}:
        return FakeProvider()
    if selected in {"openai", "openai-compatible", "real"}:
        return OpenAICompatibleProvider()
    raise APIError(503, "LLM_PROVIDER_INVALID", "未知的模型提供方")
