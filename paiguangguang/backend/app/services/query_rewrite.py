from __future__ import annotations

import json
from typing import Any

from app.ai.deepseek import DeepSeekClient, DeepSeekError
from app.core.config import get_settings
from app.schemas.rag import RagQueryRewriteData, RagQueryRewriteMetadata
from app.services.rag_cache import build_shared_cache_key, cache_ttl_seconds, get_rag_cache_adapter


def build_query_rewrite_system_prompt() -> str:
    return (
        "You rewrite user questions into short retrieval queries for a RAG system.\n"
        "Return only valid JSON with keys original_question and rewritten_queries.\n"
        "The original_question value must echo the user's input exactly.\n"
        "The rewritten_queries value must be an array of zero or more concise retrieval queries.\n"
        "Do not add commentary, numbering, markdown, or explanations.\n"
        "Preserve exact identifiers, paths, code symbols, and quoted phrases when present."
    )


class QueryRewriteService:
    def __init__(
        self,
        client: DeepSeekClient | None = None,
        *,
        enabled: bool | None = None,
        model: str | None = None,
        cache_adapter=None,
    ) -> None:
        settings = get_settings()
        self.client = client or DeepSeekClient(settings)
        self.enabled = settings.query_rewrite_enabled if enabled is None else enabled
        self.model = model or settings.query_rewrite_model or settings.deepseek_chat_model
        self.cache_adapter = cache_adapter or get_rag_cache_adapter(settings)

    def rewrite(self, question: str, *, cache_bypass: bool = False) -> RagQueryRewriteData:
        result, _cache_hit = self.rewrite_with_cache_info(question, cache_bypass=cache_bypass)
        return result

    def rewrite_with_cache_info(
        self,
        question: str,
        *,
        cache_bypass: bool = False,
    ) -> tuple[RagQueryRewriteData, bool]:
        original_question = question.strip()
        if not self.enabled:
            result = self._build_result(
                original_question=original_question,
                rewritten_queries=[],
                status="disabled",
                fallback_reason=None,
                model=self.model,
            )
            self._store_cache(original_question, result, cache_bypass=cache_bypass)
            return result, False

        if not cache_bypass:
            cached = self._load_cache(original_question)
            if cached is not None:
                return cached, True

        try:
            payload = self._rewrite_with_model(original_question)
            rewritten_queries = self._normalize_queries(payload.get("rewritten_queries"), original_question)
            if not rewritten_queries:
                result = self._build_result(
                    original_question=original_question,
                    rewritten_queries=[],
                    status="fallback",
                    fallback_reason="Model returned no usable rewritten queries",
                    model=self.model,
                )
                self._store_cache(original_question, result, cache_bypass=cache_bypass)
                return result, False

            result = self._build_result(
                original_question=original_question,
                rewritten_queries=rewritten_queries,
                status="ok",
                fallback_reason=None,
                model=self.model,
            )
            self._store_cache(original_question, result, cache_bypass=cache_bypass)
            return result, False
        except (ValueError, TypeError, json.JSONDecodeError, DeepSeekError) as exc:
            result = self._build_result(
                original_question=original_question,
                rewritten_queries=[],
                status="fallback",
                fallback_reason=str(exc),
                model=self.model,
            )
            self._store_cache(original_question, result, cache_bypass=cache_bypass)
            return result, False

    def _load_cache(self, original_question: str) -> RagQueryRewriteData | None:
        cache_key = build_shared_cache_key(
            "rag:rewrite",
            model_version=self.model,
            payload={
                "question": original_question,
                "enabled": self.enabled,
                "model": self.model,
            },
        )
        cached = self.cache_adapter.get(cache_key)
        if isinstance(cached, dict):
            try:
                return RagQueryRewriteData.model_validate(cached)
            except Exception:
                return None
        return None

    def _store_cache(self, original_question: str, result: RagQueryRewriteData, *, cache_bypass: bool) -> None:
        if cache_bypass:
            return
        cache_key = build_shared_cache_key(
            "rag:rewrite",
            model_version=self.model,
            payload={
                "question": original_question,
                "enabled": self.enabled,
                "model": self.model,
            },
        )
        self.cache_adapter.set(
            cache_key,
            result.model_dump(mode="json"),
            ttl_seconds=cache_ttl_seconds("rag:rewrite"),
        )

    def _rewrite_with_model(self, question: str) -> dict[str, Any]:
        result = self.client.chat_completions(
            [
                {"role": "system", "content": build_query_rewrite_system_prompt()},
                {
                    "role": "user",
                    "content": (
                        "Rewrite this question for retrieval.\n"
                        f"Question: {question}\n\n"
                        "Return the JSON object only."
                    ),
                },
            ],
            model=self.model,
            temperature=0.0,
        )
        content = self._extract_reply(result)
        payload = json.loads(self._strip_code_fence(content))
        if not isinstance(payload, dict):
            raise ValueError("Query rewrite returned an invalid payload")
        return payload

    @staticmethod
    def _extract_reply(payload: dict[str, Any]) -> str:
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise DeepSeekError("DeepSeek returned no choices")

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise DeepSeekError("DeepSeek returned an invalid choice payload")

        message = first_choice.get("message")
        if not isinstance(message, dict):
            raise DeepSeekError("DeepSeek returned an invalid message payload")

        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise DeepSeekError("DeepSeek returned an empty reply")

        return content.strip()

    @staticmethod
    def _strip_code_fence(content: str) -> str:
        text = content.strip()
        if text.startswith("```"):
            lines = [line for line in text.splitlines() if not line.startswith("```")]
            text = "\n".join(lines).strip()
        return text

    @staticmethod
    def _normalize_queries(value: object, original_question: str) -> list[str]:
        if not isinstance(value, list):
            raise ValueError("Query rewrite returned an invalid rewritten_queries field")

        normalized: list[str] = []
        seen: set[str] = {original_question.strip().casefold()}
        for item in value:
            if not isinstance(item, str):
                continue
            candidate = item.strip()
            if not candidate:
                continue
            key = candidate.casefold()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(candidate)
        return normalized

    @staticmethod
    def _build_result(
        *,
        original_question: str,
        rewritten_queries: list[str],
        status: str,
        fallback_reason: str | None,
        model: str,
    ) -> RagQueryRewriteData:
        return RagQueryRewriteData(
            original_question=original_question,
            rewritten_queries=rewritten_queries,
            metadata=RagQueryRewriteMetadata(
                enabled=status != "disabled",
                model=model,
                status=status,
                fallback_reason=fallback_reason,
                rewritten_query_count=len(rewritten_queries),
            ),
        )


_QUERY_REWRITE_SERVICE = QueryRewriteService()


def get_query_rewrite_service() -> QueryRewriteService:
    return _QUERY_REWRITE_SERVICE
