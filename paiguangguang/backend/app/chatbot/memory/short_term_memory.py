from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterator

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.llm.provider import LLMMessage
from app.chatbot.memory.redis_adapter import RedisShortTermMemoryAdapter
from app.chatbot.models.conversation import ChatbotConversation, ChatbotConversationSummary
from app.chatbot.models.message import ChatbotMessage
from app.core.config import Settings, get_settings
from app.chatbot.observability import log_chatbot_event


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class ShortTermMemoryContext:
    summary: str | None
    recent_messages: tuple[LLMMessage, ...]
    state: dict[str, Any]


class ShortTermMemoryService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        settings: Settings | None = None,
        redis_module: Any | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.settings = settings or get_settings()
        self._schema_version = max(1, int(self.settings.chatbot_redis_schema_version))
        self._ttl_seconds = max(1, int(self.settings.chatbot_short_memory_ttl_seconds))
        self._recent_limit = max(1, int(self.settings.chatbot_recent_message_limit))
        self._adapter: RedisShortTermMemoryAdapter | None = None
        if self.settings.redis_url:
            try:
                self._adapter = RedisShortTermMemoryAdapter(
                    self.settings.redis_url,
                    environment=self.settings.chatbot_env,
                    schema_version=self._schema_version,
                    redis_module=redis_module,
                )
            except Exception as exc:  # pragma: no cover - defensive degrade
                self._adapter = None
                log_chatbot_event("chatbot.redis.degraded", reason=type(exc).__name__, source="short_memory")

    def load_history(
        self,
        session: Session,
        user_id: str,
        conversation_id: str,
        *,
        before_sequence_number: int | None = None,
    ) -> tuple[LLMMessage, ...]:
        context = self.load_context(
            session,
            user_id,
            conversation_id,
            before_sequence_number=before_sequence_number,
        )
        history: list[LLMMessage] = []
        if context.summary:
            history.append(LLMMessage(role="system", content=context.summary))
        history.extend(context.recent_messages)
        return tuple(history)

    def load_context(
        self,
        session: Session,
        user_id: str,
        conversation_id: str,
        *,
        before_sequence_number: int | None = None,
    ) -> ShortTermMemoryContext:
        resolved_before = before_sequence_number or self._resolve_before_sequence_number(session, conversation_id)
        if self._adapter is not None:
            try:
                cached = self._read_cached_context(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    before_sequence_number=resolved_before,
                )
                if cached is not None:
                    return cached
            except Exception as exc:
                log_chatbot_event(
                    "chatbot.redis.degraded",
                    reason=type(exc).__name__,
                    source="short_memory",
                    user_id=user_id,
                    conversation_id=conversation_id,
                )
                self._adapter = None

        context = self._rebuild_context_from_postgres(
            session,
            user_id,
            conversation_id,
            before_sequence_number=resolved_before,
        )
        self._best_effort_cache(user_id, conversation_id, context, resolved_before)
        return context

    def refresh_context(self, user_id: str, conversation_id: str) -> ShortTermMemoryContext | None:
        with self.session_factory() as session:
            try:
                resolved_before = self._resolve_before_sequence_number(session, conversation_id)
                context = self._rebuild_context_from_postgres(
                    session,
                    user_id,
                    conversation_id,
                    before_sequence_number=resolved_before,
                )
            except Exception:
                return None
            self._best_effort_cache(user_id, conversation_id, context, resolved_before)
            return context

    def clear_conversation(self, user_id: str, conversation_id: str) -> None:
        if not self.settings.redis_url:
            return
        if self._adapter is None:
            raise RuntimeError("Redis short-term memory is unavailable")
        for memory_type in ("summary", "recent", "state"):
            self._adapter.delete(
                user_id=user_id,
                conversation_id=conversation_id,
                memory_type=memory_type,
            )

    def _read_cached_context(
        self,
        *,
        user_id: str,
        conversation_id: str,
        before_sequence_number: int,
    ) -> ShortTermMemoryContext | None:
        assert self._adapter is not None
        summary_payload = self._adapter.get(user_id=user_id, conversation_id=conversation_id, memory_type="summary")
        recent_payload = self._adapter.get(user_id=user_id, conversation_id=conversation_id, memory_type="recent")
        state_payload = self._adapter.get(user_id=user_id, conversation_id=conversation_id, memory_type="state")
        if summary_payload is None or recent_payload is None or state_payload is None:
            return None
        if not self._payload_is_current(summary_payload, recent_payload, state_payload, before_sequence_number):
            return None
        return ShortTermMemoryContext(
            summary=summary_payload.get("summary"),
            recent_messages=tuple(
                LLMMessage(role=item["role"], content=item["content"])
                for item in recent_payload.get("items", [])
            ),
            state=dict(state_payload),
        )

    def _payload_is_current(
        self,
        summary_payload: dict[str, Any],
        recent_payload: dict[str, Any],
        state_payload: dict[str, Any],
        before_sequence_number: int,
    ) -> bool:
        versions = {
            summary_payload.get("schema_version"),
            recent_payload.get("schema_version"),
            state_payload.get("schema_version"),
        }
        if versions != {self._schema_version}:
            return False
        if state_payload.get("before_sequence_number") != before_sequence_number:
            return False
        return True

    def _rebuild_context_from_postgres(
        self,
        session: Session,
        user_id: str,
        conversation_id: str,
        *,
        before_sequence_number: int,
    ) -> ShortTermMemoryContext:
        conversation = session.scalar(
            select(ChatbotConversation).where(
                ChatbotConversation.id == conversation_id,
                ChatbotConversation.user_id == user_id,
                ChatbotConversation.deleted_at.is_(None),
            )
        )
        if conversation is None:
            raise ValueError("Conversation not found")

        summary_row = session.scalar(
            select(ChatbotConversationSummary)
            .where(
                ChatbotConversationSummary.conversation_id == conversation_id,
                ChatbotConversationSummary.status == "completed",
            )
            .order_by(desc(ChatbotConversationSummary.summary_version), desc(ChatbotConversationSummary.updated_at), desc(ChatbotConversationSummary.id))
            .limit(1)
        )
        summary_text = summary_row.summary if summary_row is not None else None
        summary_version = summary_row.summary_version if summary_row is not None else None
        summary_end_sequence = summary_row.end_sequence if summary_row is not None else None
        source_message_ids: list[str] = []

        recent_rows = list(
            session.scalars(
                select(ChatbotMessage)
                .where(
                    ChatbotMessage.conversation_id == conversation_id,
                    ChatbotMessage.user_id == user_id,
                    ChatbotMessage.sequence_number < before_sequence_number,
                    ChatbotMessage.status == "completed",
                    ChatbotMessage.role.in_(("user", "assistant")),
                )
                .order_by(desc(ChatbotMessage.sequence_number), desc(ChatbotMessage.id))
                .limit(self._recent_limit)
            )
        )
        recent_messages = tuple(
            LLMMessage(role=row.role, content=row.content)
            for row in reversed(recent_rows)
        )
        recent_start_sequence = recent_rows[-1].sequence_number if recent_rows else None
        recent_end_sequence = recent_rows[0].sequence_number if recent_rows else None
        state = {
            "schema_version": self._schema_version,
            "environment": self.settings.chatbot_env,
            "conversation_id": conversation_id,
            "user_id": user_id,
            "before_sequence_number": before_sequence_number,
            "summary_version": summary_version,
            "summary_end_sequence": summary_end_sequence,
            "recent_limit": self._recent_limit,
            "recent_count": len(recent_messages),
            "recent_start_sequence": recent_start_sequence,
            "recent_end_sequence": recent_end_sequence,
            "source_message_ids": source_message_ids,
            "updated_at": _utcnow().isoformat(),
        }
        return ShortTermMemoryContext(summary=summary_text, recent_messages=recent_messages, state=state)

    def _best_effort_cache(
        self,
        user_id: str,
        conversation_id: str,
        context: ShortTermMemoryContext,
        before_sequence_number: int,
    ) -> None:
        if self._adapter is None:
            return
        try:
            self._adapter.set(
                user_id=user_id,
                conversation_id=conversation_id,
                memory_type="summary",
                value=self._summary_payload(context, before_sequence_number),
                ttl_seconds=self._ttl_seconds,
            )
            self._adapter.set(
                user_id=user_id,
                conversation_id=conversation_id,
                memory_type="recent",
                value=self._recent_payload(context, before_sequence_number),
                ttl_seconds=self._ttl_seconds,
            )
            self._adapter.set(
                user_id=user_id,
                conversation_id=conversation_id,
                memory_type="state",
                value=context.state,
                ttl_seconds=self._ttl_seconds,
            )
        except Exception as exc:  # pragma: no cover - defensive degrade
            log_chatbot_event(
                "chatbot.redis.degraded",
                reason=type(exc).__name__,
                source="short_memory",
                user_id=user_id,
                conversation_id=conversation_id,
            )
            self._adapter = None

    def _summary_payload(self, context: ShortTermMemoryContext, before_sequence_number: int) -> dict[str, Any]:
        summary_version = context.state.get("summary_version")
        summary_end_sequence = context.state.get("summary_end_sequence")
        return {
            "schema_version": self._schema_version,
            "before_sequence_number": before_sequence_number,
            "summary": context.summary,
            "summary_version": summary_version,
            "summary_end_sequence": summary_end_sequence,
            "source_message_ids": context.state.get("source_message_ids", []),
            "updated_at": context.state.get("updated_at"),
        }

    def _recent_payload(self, context: ShortTermMemoryContext, before_sequence_number: int) -> dict[str, Any]:
        return {
            "schema_version": self._schema_version,
            "before_sequence_number": before_sequence_number,
            "recent_limit": self._recent_limit,
            "items": [
                {"role": message.role, "content": message.content}
                for message in context.recent_messages
            ],
            "updated_at": context.state.get("updated_at"),
        }

    def _resolve_before_sequence_number(self, session: Session, conversation_id: str) -> int:
        conversation = session.scalar(
            select(ChatbotConversation).where(
                ChatbotConversation.id == conversation_id,
                ChatbotConversation.deleted_at.is_(None),
            )
        )
        if conversation is None:
            raise ValueError("Conversation not found")
        latest_sequence = session.scalar(
            select(func.max(ChatbotMessage.sequence_number)).where(ChatbotMessage.conversation_id == conversation_id)
        )
        if not isinstance(latest_sequence, int):
            latest_sequence = 0
        return max(conversation.next_sequence, latest_sequence + 1)
