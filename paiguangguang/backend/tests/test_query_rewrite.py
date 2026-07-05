from __future__ import annotations

import json

import httpx

from app.ai.deepseek import DeepSeekClient
from app.services.query_rewrite import QueryRewriteService


def _build_client(content: str) -> DeepSeekClient:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": content,
                        }
                    }
                ]
            },
        )

    return DeepSeekClient(api_key="test-key", transport=httpx.MockTransport(handler))


def test_query_rewrite_service_returns_deterministic_fallback_when_disabled() -> None:
    service = QueryRewriteService(enabled=False)

    result = service.rewrite("How should I deploy the site?")

    assert result.original_question == "How should I deploy the site?"
    assert result.rewritten_queries == []
    assert result.metadata.enabled is False
    assert result.metadata.status == "disabled"
    assert result.metadata.fallback_reason is None
    assert result.metadata.rewritten_query_count == 0


def test_query_rewrite_service_uses_model_output_when_enabled() -> None:
    client = _build_client(
        json.dumps(
            {
                "original_question": "How should I deploy the site?",
                "rewritten_queries": [
                    "deployment steps for the site",
                    "production deployment workflow",
                ],
            }
        )
    )
    service = QueryRewriteService(client=client, enabled=True)

    result = service.rewrite("How should I deploy the site?")

    assert result.original_question == "How should I deploy the site?"
    assert result.rewritten_queries == [
        "deployment steps for the site",
        "production deployment workflow",
    ]
    assert result.metadata.enabled is True
    assert result.metadata.status == "ok"
    assert result.metadata.fallback_reason is None
    assert result.metadata.rewritten_query_count == 2


def test_query_rewrite_service_falls_back_on_invalid_or_empty_output() -> None:
    invalid_client = _build_client("not json")
    empty_client = _build_client(json.dumps({"rewritten_queries": []}))
    invalid_service = QueryRewriteService(client=invalid_client, enabled=True)
    empty_service = QueryRewriteService(client=empty_client, enabled=True)

    invalid_result = invalid_service.rewrite("What changed?")
    empty_result = empty_service.rewrite("What changed?")

    assert invalid_result.original_question == "What changed?"
    assert invalid_result.rewritten_queries == []
    assert invalid_result.metadata.status == "fallback"
    assert invalid_result.metadata.fallback_reason

    assert empty_result.original_question == "What changed?"
    assert empty_result.rewritten_queries == []
    assert empty_result.metadata.status == "fallback"
    assert empty_result.metadata.fallback_reason == "Model returned no usable rewritten queries"
