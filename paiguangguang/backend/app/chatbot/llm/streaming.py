from __future__ import annotations

import json
from typing import Any, Iterable, Iterator

import httpx

from app.chatbot.llm.exceptions import LLMProtocolError


def iter_sse_payloads(response: httpx.Response) -> Iterator[str]:
    data_lines: list[str] = []
    for line in response.iter_lines():
        if line is None:
            continue
        if line == "":
            if data_lines:
                yield "\n".join(data_lines)
                data_lines.clear()
            continue
        if line.startswith(":"):
            continue
        if line.startswith("data:"):
            data_lines.append(line[5:].lstrip())
            continue
        if line.startswith("event:") or line.startswith("id:") or line.startswith("retry:"):
            continue
        raise LLMProtocolError(f"Unsupported SSE line: {line}")
    if data_lines:
        yield "\n".join(data_lines)


def decode_sse_payload(raw_payload: str) -> dict[str, Any] | str:
    payload = raw_payload.strip()
    if payload == "[DONE]":
        return payload
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise LLMProtocolError(f"Invalid streaming JSON payload: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise LLMProtocolError("Streaming payload must be a JSON object")
    return data
