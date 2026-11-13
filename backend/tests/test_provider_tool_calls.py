import asyncio

import pytest
from pydantic import SecretStr

from app.config import settings
from app.core.errors import APIError
from app.modules.runtime.providers import OpenAICompatibleProvider


class _Response:
    status_code = 200

    def __init__(self, lines: list[str]):
        self._lines = lines

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def aiter_lines(self):
        for line in self._lines:
            yield line


class _Client:
    def __init__(self, lines: list[str]):
        self._lines = lines

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    def stream(self, *_args, **_kwargs):
        return _Response(self._lines)


def _run(provider: OpenAICompatibleProvider):
    async def collect():
        return [chunk async for chunk in provider.stream([{"role": "user", "content": "查"}])]

    return asyncio.run(collect())


def _configure(monkeypatch):
    monkeypatch.setattr(settings, "llm_base_url", "http://local.test/v1")
    monkeypatch.setattr(settings, "llm_model", "local-model")
    monkeypatch.setattr(settings, "llm_api_key", SecretStr("test-key"))


def test_stream_assembles_multiple_fragmented_tool_calls(monkeypatch):
    _configure(monkeypatch)
    lines = [
        'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"call-a","type":"function","function":{"name":"search","arguments":"{\\"query\\":"}}]}}]}',
        'data: {"choices":[{"delta":{"tool_calls":[{"index":1,"id":"call-b","type":"function","function":{"name":"lookup","arguments":"{\\"id\\":"}}]}}]}',
        'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"function":{"arguments":"\\"北京\\"}"}}]}}]}',
        'data: {"choices":[{"delta":{"tool_calls":[{"index":1,"function":{"arguments":"42}"}}]}}]}',
        'data: {"choices":[{"delta":{},"finish_reason":"tool_calls"}]}',
        'data: [DONE]',
    ]
    monkeypatch.setattr(
        "app.modules.runtime.providers.httpx.AsyncClient",
        lambda **_kwargs: _Client(lines),
    )

    chunks = _run(OpenAICompatibleProvider())

    assert chunks[-1].done is True
    assert chunks[-1].tool_calls == [
        {
            "id": "call-a",
            "type": "function",
            "function": {"name": "search", "arguments": '{"query":"北京"}'},
        },
        {
            "id": "call-b",
            "type": "function",
            "function": {"name": "lookup", "arguments": '{"id":42}'},
        },
    ]


def test_stream_assigns_stable_id_when_provider_omits_id(monkeypatch):
    _configure(monkeypatch)
    lines = [
        'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"type":"function","function":{"name":"ping","arguments":"{}"}}]}}]}',
        'data: {"choices":[{"delta":{},"finish_reason":"tool_calls"}]}',
        'data: [DONE]',
    ]
    monkeypatch.setattr(
        "app.modules.runtime.providers.httpx.AsyncClient",
        lambda **_kwargs: _Client(lines),
    )

    chunks = _run(OpenAICompatibleProvider())

    assert chunks[-1].tool_calls[0]["id"].startswith("tool_call_")


def test_stream_rejects_invalid_tool_arguments(monkeypatch):
    _configure(monkeypatch)
    lines = [
        'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"call-bad","type":"function","function":{"name":"search","arguments":"{bad"}}]}}]}',
        'data: {"choices":[{"delta":{},"finish_reason":"tool_calls"}]}',
        'data: [DONE]',
    ]
    monkeypatch.setattr(
        "app.modules.runtime.providers.httpx.AsyncClient",
        lambda **_kwargs: _Client(lines),
    )

    with pytest.raises(APIError) as raised:
        _run(OpenAICompatibleProvider())

    assert raised.value.code == "LLM_TOOL_CALL_INVALID"


def test_stream_rejects_unparseable_model_event(monkeypatch):
    _configure(monkeypatch)
    lines = ["data: definitely-not-json"]
    monkeypatch.setattr(
        "app.modules.runtime.providers.httpx.AsyncClient",
        lambda **_kwargs: _Client(lines),
    )

    with pytest.raises(APIError) as raised:
        _run(OpenAICompatibleProvider())

    assert raised.value.code == "LLM_INVALID_RESPONSE"


@pytest.mark.parametrize("finish_reason", ["length", "content_filter"])
def test_stream_rejects_non_success_finish_reason(monkeypatch, finish_reason):
    _configure(monkeypatch)
    lines = [
        f'data: {{"choices":[{{"delta":{{"content":"partial"}},"finish_reason":"{finish_reason}"}}]}}',
        "data: [DONE]",
    ]
    monkeypatch.setattr(
        "app.modules.runtime.providers.httpx.AsyncClient",
        lambda **_kwargs: _Client(lines),
    )

    with pytest.raises(APIError) as raised:
        _run(OpenAICompatibleProvider())

    assert raised.value.code == "LLM_FINISH_UNSUPPORTED"


def test_stream_rejects_missing_finish_reason(monkeypatch):
    _configure(monkeypatch)
    lines = [
        'data: {"choices":[{"delta":{"content":"partial"}}]}',
        "data: [DONE]",
    ]
    monkeypatch.setattr(
        "app.modules.runtime.providers.httpx.AsyncClient",
        lambda **_kwargs: _Client(lines),
    )

    with pytest.raises(APIError) as raised:
        _run(OpenAICompatibleProvider())

    assert raised.value.code == "LLM_FINISH_MISSING"


def test_stream_rejects_tool_call_without_index(monkeypatch):
    _configure(monkeypatch)
    lines = [
        'data: {"choices":[{"delta":{"tool_calls":[{"id":"call-no-index","type":"function","function":{"name":"ping","arguments":"{}"}}]}}]}',
        'data: {"choices":[{"delta":{},"finish_reason":"tool_calls"}]}',
        "data: [DONE]",
    ]
    monkeypatch.setattr(
        "app.modules.runtime.providers.httpx.AsyncClient",
        lambda **_kwargs: _Client(lines),
    )

    with pytest.raises(APIError) as raised:
        _run(OpenAICompatibleProvider())

    assert raised.value.code == "LLM_TOOL_CALL_INVALID"


def test_stream_assembles_fragmented_function_name(monkeypatch):
    _configure(monkeypatch)
    lines = [
        'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"call-name","type":"function","function":{"name":"se","arguments":"{}"}}]}}]}',
        'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"function":{"name":"arch"}}]}}]}',
        'data: {"choices":[{"delta":{},"finish_reason":"tool_calls"}]}',
        "data: [DONE]",
    ]
    monkeypatch.setattr(
        "app.modules.runtime.providers.httpx.AsyncClient",
        lambda **_kwargs: _Client(lines),
    )

    chunks = _run(OpenAICompatibleProvider())

    assert chunks[-1].tool_calls[0]["function"]["name"] == "search"
