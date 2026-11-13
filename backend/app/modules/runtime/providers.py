import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.config import settings
from app.core.errors import APIError


@dataclass
class LLMChunk:
    text: str = ""
    # OpenAI-compatible tool calls use the wire representation so Runtime can
    # persist the assistant message verbatim before executing any tool.  A
    # chunk may contain more than one call; ``function.arguments`` is the
    # assembled JSON string (rather than a parsed object) to preserve the
    # model's exact payload for trace/audit purposes.
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
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
    supports_output_budget = True

    def __init__(self) -> None:
        if (
            not settings.llm_base_url.strip()
            or not settings.llm_model.strip()
            or settings.llm_api_key is None
            or not settings.llm_api_key.get_secret_value().strip()
        ):
            raise APIError(
                503,
                "REAL_PROVIDER_NOT_CONFIGURED",
                "真实模型未配置，已拒绝执行",
            )

    async def stream(
        self, messages: list[dict[str, str]], *, tools: list[dict[str, Any]] | None = None,
        max_tokens: int | None = None,
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
        if max_tokens is not None:
            body["max_tokens"] = max_tokens
        timeout = httpx.Timeout(settings.llm_timeout_seconds)
        completed = False
        finish_reason: str | None = None
        request_nonce = uuid.uuid4().hex
        tool_call_parts: dict[int, dict[str, Any]] = {}
        token_input = 0
        token_output = 0

        def collect_tool_calls(delta: Any) -> None:
            """Merge one OpenAI ``delta.tool_calls`` fragment into the stream.

            Providers are allowed to omit ``id``, ``type`` or function fields
            from continuation fragments.  Index is therefore the only stable
            key while the stream is in flight; a deterministic fallback id is
            assigned when the provider never sends one.
            """

            if delta is None:
                return
            if not isinstance(delta, list):
                raise APIError(502, "LLM_TOOL_CALL_INVALID", "模型工具调用格式无效")
            for item in delta:
                if not isinstance(item, dict):
                    raise APIError(502, "LLM_TOOL_CALL_INVALID", "模型工具调用格式无效")
                if "index" not in item:
                    raise APIError(502, "LLM_TOOL_CALL_INVALID", "模型工具调用缺少索引")
                raw_index = item["index"]
                if isinstance(raw_index, bool) or not isinstance(raw_index, int):
                    raise APIError(502, "LLM_TOOL_CALL_INVALID", "模型工具调用索引无效")
                index = raw_index
                if index < 0 or index >= settings.run_max_steps:
                    raise APIError(502, "LLM_TOOL_CALL_INVALID", "模型工具调用索引无效")
                current = tool_call_parts.setdefault(
                    index,
                    {
                        "id": f"tool_call_{request_nonce}_{index}",
                        "type": "function",
                        "function": {"name": "", "arguments": ""},
                    },
                )
                call_id = item.get("id")
                if call_id is not None:
                    if not isinstance(call_id, str) or not call_id.strip() or len(call_id) > 128:
                        raise APIError(502, "LLM_TOOL_CALL_INVALID", "模型工具调用 ID 无效")
                    if current.get("provided_id") and current["id"] != call_id:
                        raise APIError(502, "LLM_TOOL_CALL_INVALID", "模型工具调用 ID 不一致")
                    current["id"] = call_id
                    current["provided_id"] = True
                call_type = item.get("type")
                if call_type is not None:
                    if call_type != "function":
                        raise APIError(502, "LLM_TOOL_CALL_INVALID", "模型工具调用类型无效")
                    current["type"] = "function"
                function = item.get("function")
                if function is None:
                    continue
                if not isinstance(function, dict):
                    raise APIError(502, "LLM_TOOL_CALL_INVALID", "模型工具调用函数格式无效")
                name = function.get("name")
                if name is not None:
                    if not isinstance(name, str):
                        raise APIError(502, "LLM_TOOL_CALL_INVALID", "模型工具名称无效")
                    # A few compatible providers split the function name in
                    # the same way as arguments.  Keep identical retries
                    # idempotent while joining genuine fragments.
                    previous_name = current["function"]["name"]
                    if not previous_name:
                        current["function"]["name"] = name
                    elif name == previous_name:
                        pass
                    elif name.startswith(previous_name):
                        current["function"]["name"] = name
                    else:
                        current["function"]["name"] = previous_name + name
                arguments = function.get("arguments")
                if arguments is not None:
                    if not isinstance(arguments, str):
                        raise APIError(502, "LLM_TOOL_CALL_INVALID", "模型工具参数格式无效")
                    current["function"]["arguments"] += arguments
                    if len(current["function"]["arguments"].encode("utf-8")) > 16 * 1024:
                        raise APIError(502, "LLM_TOOL_CALL_INVALID", "模型工具参数过大")

        def finalize_tool_calls() -> list[dict[str, Any]]:
            calls: list[dict[str, Any]] = []
            for index in sorted(tool_call_parts):
                call = tool_call_parts[index]
                name = call["function"]["name"].strip()
                arguments = call["function"]["arguments"]
                if not name:
                    raise APIError(502, "LLM_TOOL_CALL_INVALID", "模型未提供工具名称")
                if not arguments.strip():
                    raise APIError(502, "LLM_TOOL_CALL_INVALID", "模型未提供工具参数")
                try:
                    parsed = json.loads(arguments)
                except json.JSONDecodeError as error:
                    raise APIError(502, "LLM_TOOL_CALL_INVALID", "模型工具参数不是有效 JSON") from error
                if not isinstance(parsed, dict):
                    raise APIError(502, "LLM_TOOL_CALL_INVALID", "模型工具参数必须是 JSON 对象")
                calls.append(
                    {
                        "id": call["id"],
                        "type": "function",
                        "function": {"name": name, "arguments": arguments},
                    }
                )
            return calls

        try:
            async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
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
                        except json.JSONDecodeError as error:
                            raise APIError(502, "LLM_INVALID_RESPONSE", "模型返回了无法解析的数据") from error
                        if not isinstance(data, dict):
                            raise APIError(502, "LLM_INVALID_RESPONSE", "模型返回格式无效")
                        usage = data.get("usage")
                        if isinstance(usage, dict):
                            try:
                                prompt_tokens = usage.get("prompt_tokens") or 0
                                completion_tokens = usage.get("completion_tokens") or 0
                                if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in (prompt_tokens, completion_tokens)):
                                    raise ValueError()
                                token_input = max(token_input, prompt_tokens)
                                token_output = max(token_output, completion_tokens)
                            except ValueError as error:
                                raise APIError(502, "LLM_INVALID_RESPONSE", "模型用量格式无效") from error
                        choices = data.get("choices") or []
                        if not choices:
                            continue
                        choice = choices[0]
                        if not isinstance(choice, dict):
                            raise APIError(502, "LLM_INVALID_RESPONSE", "模型返回格式无效")
                        delta = choice.get("delta") or {}
                        if not isinstance(delta, dict):
                            raise APIError(502, "LLM_INVALID_RESPONSE", "模型增量格式无效")
                        collect_tool_calls(delta.get("tool_calls"))
                        choice_finish_reason = choice.get("finish_reason")
                        if choice_finish_reason is not None:
                            if choice_finish_reason not in {"stop", "tool_calls"}:
                                raise APIError(
                                    502,
                                    "LLM_FINISH_UNSUPPORTED",
                                    "模型以不可接受的原因结束",
                                )
                            if finish_reason is not None and finish_reason != choice_finish_reason:
                                raise APIError(502, "LLM_FINISH_INVALID", "模型结束状态不一致")
                            finish_reason = choice_finish_reason
                        text = delta.get("content") or ""
                        if not isinstance(text, str):
                            raise APIError(502, "LLM_INVALID_RESPONSE", "模型文本格式无效")
                        if text:
                            yield LLMChunk(text=text)
        except httpx.TimeoutException as error:
            raise APIError(504, "LLM_TIMEOUT", "模型请求超时") from error
        except httpx.HTTPError as error:
            raise APIError(503, "LLM_UNAVAILABLE", "模型服务不可达") from error
        if not completed:
            raise APIError(502, "LLM_STREAM_TRUNCATED", "模型流提前中断")
        if finish_reason is None:
            raise APIError(502, "LLM_FINISH_MISSING", "模型缺少结束状态")
        if (finish_reason == "tool_calls") != bool(tool_call_parts):
            raise APIError(502, "LLM_FINISH_INVALID", "模型结束状态与工具调用不一致")
        # Runtime consumes tool calls from the terminal chunk so an assistant
        # message is persisted atomically with the provider turn.
        calls = finalize_tool_calls() if tool_call_parts else []
        yield LLMChunk(
            tool_calls=calls,
            done=True,
            token_input=token_input,
            token_output=token_output,
        )


def build_provider(_requested_mode: str | None = None):
    """Build the provider selected by trusted server configuration.

    ``_requested_mode`` remains an ignored compatibility parameter for older
    test doubles and callers. Client payloads never select the provider.
    """
    selected = settings.llm_provider.strip().lower()
    if selected in {"fake", "test"}:
        if settings.environment.lower() in {"production", "prod"}:
            raise APIError(
                503,
                "REAL_PROVIDER_NOT_CONFIGURED",
                "生产环境禁止使用 Fake Provider",
            )
        return FakeProvider()
    if selected in {"openai", "openai-compatible", "real"}:
        return OpenAICompatibleProvider()
    raise APIError(503, "LLM_PROVIDER_INVALID", "未知的模型提供方")
