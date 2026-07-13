from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import re
import unicodedata
from typing import Any, Literal, Sequence

from app.chatbot.llm.client import LLMClient
from app.chatbot.llm.provider import ChatCompletionRequest, ChatCompletionResult, LLMMessage
from app.chatbot.llm.prompt_builder import PromptBuilder
from app.core.config import Settings, get_settings


MemoryAction = Literal["upsert", "forget"]


@dataclass(frozen=True, slots=True)
class MemoryDraft:
    source: Literal["rule", "llm"]
    action: MemoryAction
    memory_type: Literal["preference", "goal", "project_context", "explicit", "fact", "work_context"]
    content: str
    confidence: float
    importance: float
    status: Literal["candidate", "active"]
    source_message_ids: tuple[str, ...]
    normalized_content: str
    normalized_hash: str
    target_hash: str | None = None


_SENSITIVE_PATTERNS = (
    re.compile(r"(password|passwd|secret|token|api\s*key|payment|credit\s*card)", re.IGNORECASE),
    re.compile(r"(密码|口令|密钥|令牌|支付|银行卡|信用卡|身份证|护照|医保|病历|病史|健康|生物)", re.IGNORECASE),
)


def normalize_memory_content(content: str) -> str:
    normalized = unicodedata.normalize("NFKC", content).lower().strip()
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = normalized.strip(" 。,，.!?！？:：;；、`\"'“”‘’")
    return normalized


def build_memory_hash(memory_type: str, normalized_content: str) -> str:
    digest = hashlib.sha256()
    digest.update(memory_type.encode("utf-8"))
    digest.update(b"\0")
    digest.update(normalized_content.encode("utf-8"))
    return digest.hexdigest()


def _is_sensitive(text: str) -> bool:
    return any(pattern.search(text) for pattern in _SENSITIVE_PATTERNS)


def _strip_code_fences(content: str) -> str:
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


class MemoryExtractor:
    def __init__(
        self,
        *,
        llm_client: LLMClient | None = None,
        settings: Settings | None = None,
        prompt_builder_factory: type[PromptBuilder] = PromptBuilder,
    ) -> None:
        self.settings = settings or get_settings()
        self.llm_client = llm_client
        self._prompt_builder = prompt_builder_factory(
            prompt_version="memory-extraction-v1",
            system_prompt=(
                "You extract durable user memories for a chatbot. "
                "Return JSON only. Never include secrets, passwords, tokens, payment data, government IDs, "
                "or health/biological sensitive information."
            ),
            default_model=self.settings.chatbot_default_model,
        )

    def extract(
        self,
        *,
        user_message: str,
        assistant_message: str,
        user_id: str,
        conversation_id: str,
        source_message_ids: Sequence[str],
    ) -> list[MemoryDraft]:
        text = f"{user_message}\n{assistant_message}"
        if _is_sensitive(text):
            return []

        drafts = self._extract_rule_drafts(
            user_message=user_message,
            assistant_message=assistant_message,
            user_id=user_id,
            conversation_id=conversation_id,
            source_message_ids=source_message_ids,
        )
        if drafts:
            return drafts

        if self.llm_client is None:
            return []
        return self._extract_llm_drafts(
            user_message=user_message,
            assistant_message=assistant_message,
            user_id=user_id,
            conversation_id=conversation_id,
            source_message_ids=source_message_ids,
        )

    def _extract_rule_drafts(
        self,
        *,
        user_message: str,
        assistant_message: str,
        user_id: str,
        conversation_id: str,
        source_message_ids: Sequence[str],
    ) -> list[MemoryDraft]:
        del assistant_message, user_id, conversation_id
        normalized_sources = tuple(str(source_id) for source_id in source_message_ids)
        text = normalize_memory_content(user_message)

        if "忘记" in text:
            target = text.split("忘记", 1)[1].strip(" ：:，,。")
            if not target:
                return []
            normalized_target = normalize_memory_content(target)
            return [
                MemoryDraft(
                    source="rule",
                    action="forget",
                    memory_type="explicit",
                    content=target,
                    confidence=0.98,
                    importance=0.0,
                    status="candidate",
                    source_message_ids=normalized_sources,
                    normalized_content=normalized_target,
                    normalized_hash=build_memory_hash("explicit", normalized_target),
                    target_hash=build_memory_hash("explicit", normalized_target),
                )
            ]

        remember_target = self._parse_remember_target(text)
        if remember_target is None:
            return []

        memory_type, content, confidence, importance = remember_target
        normalized_content = normalize_memory_content(content)
        return [
            MemoryDraft(
                source="rule",
                action="upsert",
                memory_type=memory_type,
                content=content,
                confidence=confidence,
                importance=importance,
                status="active",
                source_message_ids=normalized_sources,
                normalized_content=normalized_content,
                normalized_hash=build_memory_hash(memory_type, normalized_content),
            )
        ]

    def _parse_remember_target(
        self,
        text: str,
    ) -> tuple[Literal["preference", "goal", "project_context", "explicit", "fact", "work_context"], str, float, float] | None:
        if "记住" not in text and "保存" not in text and "记录" not in text:
            return None

        patterns: list[tuple[str, str, float, float, re.Pattern[str]]] = [
            (
                "project_context",
                "项目名是",
                0.96,
                0.82,
                re.compile(r"(?:请)?(?:记住|保存|记录)(?:我的|这个|这条)?(?:项目名|项目|工程名)?(?:是|叫|为|：|:)?(?P<value>.+)"),
            ),
            (
                "preference",
                "我喜欢",
                0.93,
                0.55,
                re.compile(r"(?:请)?(?:记住|保存|记录)(?:我的|这个|这条)?(?:偏好|喜好|喜欢)(?:是|为|：|:)?(?P<value>.+)"),
            ),
            (
                "goal",
                "我的目标是",
                0.91,
                0.7,
                re.compile(r"(?:请)?(?:记住|保存|记录)(?:我的|这个|这条)?(?:目标|计划|想要|要做的事)(?:是|为|：|:)?(?P<value>.+)"),
            ),
            (
                "work_context",
                "我正在",
                0.88,
                0.68,
                re.compile(r"(?:请)?(?:记住|保存|记录)(?:我的|这个|这条)?(?:工作|负责|正在做)(?:是|为|：|:)?(?P<value>.+)"),
            ),
        ]

        for memory_type, prefix, confidence, importance, pattern in patterns:
            match = pattern.search(text)
            if not match:
                continue
            value = match.group("value").strip(" ：:，,。")
            if not value:
                continue
            content = f"{prefix}{value}"
            return memory_type, content, confidence, importance

        match = re.search(r"(?:请)?(?:记住|保存|记录)(?:我的|这个|这条)?(?P<value>.+)", text)
        if match:
            value = match.group("value").strip(" ：:，,。")
            if value:
                return "fact", value, 0.84, 0.5
        return None

    def _extract_llm_drafts(
        self,
        *,
        user_message: str,
        assistant_message: str,
        user_id: str,
        conversation_id: str,
        source_message_ids: Sequence[str],
    ) -> list[MemoryDraft]:
        prompt = (
            "Extract durable memories from the following conversation turn.\n"
            "Return a JSON array of objects with keys: action, memory_type, content, confidence, importance, status.\n"
            "Only include stable, user-owned memories.\n"
            "If nothing should be remembered, return [].\n"
            f"conversation_id={conversation_id}\n"
            f"user_id={user_id}\n"
            f"source_message_ids={list(source_message_ids)}\n"
            "USER MESSAGE:\n"
            f"{user_message}\n"
            "ASSISTANT MESSAGE:\n"
            f"{assistant_message}\n"
        )
        request = self._prompt_builder.build_request(
            request_id=f"{conversation_id}:{user_id}:memory-extract",
            model=self.settings.chatbot_default_model,
            user_message=prompt,
            extra={
                "conversation_id": conversation_id,
                "user_id": user_id,
                "source_message_ids": list(source_message_ids),
            },
        )
        result = self.llm_client.complete(request)
        return self._parse_llm_result(result, source_message_ids=source_message_ids)

    def _parse_llm_result(
        self,
        result: ChatCompletionResult,
        *,
        source_message_ids: Sequence[str],
    ) -> list[MemoryDraft]:
        raw_content = _strip_code_fences(result.message.content)
        try:
            payload = json.loads(raw_content)
        except Exception as exc:  # pragma: no cover - defensive
            raise ValueError("LLM memory extraction response must be JSON") from exc
        if isinstance(payload, dict):
            payload = [payload]
        if not isinstance(payload, list):
            raise ValueError("LLM memory extraction response must be a JSON array")

        drafts: list[MemoryDraft] = []
        normalized_sources = tuple(str(source_id) for source_id in source_message_ids)
        for item in payload:
            if not isinstance(item, dict):
                continue
            action = str(item.get("action", "upsert")).strip().lower()
            memory_type = str(item.get("memory_type", "fact")).strip()
            if action not in {"upsert", "forget"}:
                continue
            if memory_type not in {"preference", "goal", "project_context", "explicit", "fact", "work_context"}:
                continue
            content = str(item.get("content", "")).strip()
            if not content:
                continue
            confidence = float(item.get("confidence", 0.0) or 0.0)
            importance = float(item.get("importance", 0.0) or 0.0)
            status = str(item.get("status", "candidate")).strip().lower()
            status = "active" if status == "active" else "candidate"
            normalized_content = normalize_memory_content(content)
            normalized_hash = build_memory_hash(memory_type, normalized_content)
            target_hash = normalized_hash if action == "forget" else None
            drafts.append(
                MemoryDraft(
                    source="llm",
                    action=action,  # type: ignore[arg-type]
                    memory_type=memory_type,  # type: ignore[arg-type]
                    content=content,
                    confidence=confidence,
                    importance=importance,
                    status=status,  # type: ignore[arg-type]
                    source_message_ids=normalized_sources,
                    normalized_content=normalized_content,
                    normalized_hash=normalized_hash,
                    target_hash=target_hash,
                )
            )
        return drafts
