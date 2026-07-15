from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from time import perf_counter
from typing import Any, Iterator
from uuid import UUID, uuid4

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.llm.client import LLMClient
from app.chatbot.llm.exceptions import LLMConfigurationError, LLMError, LLMProtocolError, LLMProviderError, LLMRateLimitError, LLMTimeoutError
from app.chatbot.llm.prompt_builder import PromptBuilder
from app.chatbot.llm.provider import ChatCompletionRequest, ChatCompletionResult, LLMMessage
from app.chatbot.models.conversation import ChatbotConversation, ChatbotConversationSummary
from app.chatbot.models.message import ChatbotMessage
from app.chatbot.repositories.conversation_repository import ConversationRepository, ConversationSummaryRecord
from app.core.config import Settings, get_settings
from app.chatbot.observability import log_chatbot_event


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class SummaryWindow:
    start_sequence: int
    end_sequence: int
    summary_version: int


class ConversationSummaryService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        llm_client: LLMClient,
        settings: Settings | None = None,
        prompt_builder_factory: type[PromptBuilder] = PromptBuilder,
    ) -> None:
        self.session_factory = session_factory
        self.llm_client = llm_client
        self.settings = settings or get_settings()
        self._prompt_builder_factory = prompt_builder_factory
        self._conversation_repo = ConversationRepository(session_factory)

    def maybe_generate_summary(self, user_id: str, conversation_id: str) -> ConversationSummaryRecord | None:
        user_id = self._normalize_uuid(user_id, field_name="user_id")
        conversation_id = self._normalize_uuid(conversation_id, field_name="conversation_id")
        self.reap_stale_pending()

        with self._session() as session:
            latest_summary = self._load_latest_summary(session, user_id, conversation_id)
            pending_summary = self._load_latest_pending_summary(session, user_id, conversation_id)
            if pending_summary is not None:
                return None

            conversation = session.scalar(
                select(ChatbotConversation)
                .where(
                    ChatbotConversation.id == conversation_id,
                    ChatbotConversation.user_id == user_id,
                    ChatbotConversation.deleted_at.is_(None),
                )
                .with_for_update()
            )
            if conversation is None or conversation.status != "active":
                return None

            window = self._build_summary_window(session, user_id, conversation_id, latest_summary)
            if window is None:
                return None

            pending_row = self._create_pending_summary(
                session,
                user_id=user_id,
                conversation=conversation,
                window=window,
            )

        request, source_messages = self._build_request(
            session_factory=self.session_factory,
            user_id=user_id,
            conversation_id=conversation_id,
            window=window,
            latest_summary=latest_summary,
        )

        started_at = perf_counter()
        try:
            result = self.llm_client.complete(request)
        except (LLMTimeoutError, LLMRateLimitError, LLMProviderError, LLMProtocolError, LLMConfigurationError, LLMError) as exc:
            return self._finalize_failed(pending_row.id, user_id, exc, started_at)

        return self._finalize_completed(pending_row.id, user_id, result, started_at)

    def reap_stale_pending(self, *, older_than: datetime | None = None) -> int:
        stale_before = older_than or (_utcnow() - timedelta(seconds=self.settings.chatbot_summary_pending_stale_seconds))
        count = 0
        with self._session() as session:
            rows = list(
                session.scalars(
                    select(ChatbotConversationSummary)
                    .where(
                        ChatbotConversationSummary.status == "pending",
                        ChatbotConversationSummary.updated_at < stale_before,
                    )
                    .order_by(
                        desc(ChatbotConversationSummary.updated_at),
                        desc(ChatbotConversationSummary.id),
                    )
                )
            )
            for row in rows:
                row.status = "failed"
                row.updated_at = _utcnow()
                count += 1
        if count:
            log_chatbot_event(
                "chatbot.summary.backlog",
                hits=count,
                status="reaped",
                source="postgres",
            )
        return count

    def _build_summary_window(
        self,
        session: Session,
        user_id: str,
        conversation_id: str,
        latest_summary: ConversationSummaryRecord | None,
    ) -> SummaryWindow | None:
        latest_completed_sequence = self._latest_completed_sequence(session, user_id, conversation_id)
        if latest_completed_sequence is None:
            return None

        previous_end = latest_summary.end_sequence if latest_summary is not None else 0
        start_sequence = previous_end + 1
        end_by_recent_limit = latest_completed_sequence - self.settings.chatbot_recent_message_limit
        if end_by_recent_limit < start_sequence:
            return None

        completed_count_since_summary = self._completed_message_count(session, user_id, conversation_id, previous_end)
        token_count_since_summary = self._completed_token_count(session, user_id, conversation_id, previous_end)

        count_trigger = completed_count_since_summary >= (self.settings.chatbot_summary_message_threshold + self.settings.chatbot_recent_message_limit)
        token_trigger = token_count_since_summary >= int(self.settings.chatbot_context_token_budget * self.settings.chatbot_summary_token_ratio)
        if not count_trigger and not token_trigger:
            return None

        if count_trigger:
            end_sequence = min(start_sequence + self.settings.chatbot_summary_message_threshold - 1, end_by_recent_limit)
        else:
            end_sequence = end_by_recent_limit

        if end_sequence < start_sequence:
            return None

        if latest_summary is not None and end_sequence <= latest_summary.end_sequence:
            return None

        version = (latest_summary.summary_version if latest_summary is not None else 0) + 1
        return SummaryWindow(start_sequence=start_sequence, end_sequence=end_sequence, summary_version=version)

    def _create_pending_summary(
        self,
        session: Session,
        *,
        user_id: str,
        conversation: ChatbotConversation,
        window: SummaryWindow,
    ) -> ConversationSummaryRecord:
        now = _utcnow()
        row = ChatbotConversationSummary(
            conversation_id=conversation.id,
            summary="",
            start_sequence=window.start_sequence,
            end_sequence=window.end_sequence,
            summary_version=window.summary_version,
            prompt_version=self.settings.chatbot_summary_prompt_version,
            model=self.settings.chatbot_summary_model,
            token_count=0,
            status="pending",
            created_at=now,
            updated_at=now,
        )
        session.add(row)
        session.flush()
        session.refresh(row)
        return self._conversation_repo._summary_record_from_model(row)

    def _build_request(
        self,
        *,
        session_factory: sessionmaker[Session],
        user_id: str,
        conversation_id: str,
        window: SummaryWindow,
        latest_summary: ConversationSummaryRecord | None,
    ) -> tuple[ChatCompletionRequest, tuple[LLMMessage, ...]]:
        with session_factory() as session:
            source_messages = tuple(
                self._load_source_messages(
                    session,
                    user_id,
                    conversation_id,
                    start_sequence=window.start_sequence,
                    end_sequence=window.end_sequence,
                )
            )
            previous_summary = latest_summary.summary if latest_summary is not None else None
        builder = self._prompt_builder_factory(
            prompt_version=self.settings.chatbot_summary_prompt_version,
            system_prompt=self._build_system_prompt(),
            default_model=self.settings.chatbot_summary_model,
        )
        history: tuple[LLMMessage, ...] = ()
        if previous_summary:
            history = (LLMMessage(role="assistant", content=previous_summary),)
        request = builder.build_request(
            request_id=str(uuid4()),
            model=self.settings.chatbot_summary_model,
            user_message=self._render_source_messages(source_messages, window=window, previous_summary=previous_summary),
            history=history,
        )
        return request, source_messages

    def _finalize_completed(
        self,
        summary_id: str,
        user_id: str,
        result: ChatCompletionResult,
        started_at: float,
    ) -> ConversationSummaryRecord | None:
        with self._session() as session:
            row = self._load_owned_summary(session, summary_id, user_id)
            if row is None:
                return None
            now = _utcnow()
            row.summary = result.message.content.strip()
            prompt_tokens, completion_tokens, total_tokens = self._usage_counts(result.usage)
            row.token_count = total_tokens
            row.status = "completed"
            row.updated_at = now
            session.flush()
            return self._conversation_repo._summary_record_from_model(row)

    def _finalize_failed(
        self,
        summary_id: str,
        user_id: str,
        exc: Exception,
        started_at: float,
    ) -> ConversationSummaryRecord | None:
        with self._session() as session:
            row = self._load_owned_summary(session, summary_id, user_id)
            if row is None:
                return None
            now = _utcnow()
            row.status = "failed"
            row.updated_at = now
            row.token_count = 0
            session.flush()
            log_chatbot_event(
                "chatbot.summary.failed",
                message_id=row.id,
                conversation_id=row.conversation_id,
                status="failed",
                reason=type(exc).__name__,
                source="llm",
            )
            return self._conversation_repo._summary_record_from_model(row)

    def _load_latest_summary(
        self,
        session: Session,
        user_id: str,
        conversation_id: str,
    ) -> ConversationSummaryRecord | None:
        model = session.scalar(
            select(ChatbotConversationSummary)
            .join(ChatbotConversation, ChatbotConversation.id == ChatbotConversationSummary.conversation_id)
            .where(
                ChatbotConversationSummary.conversation_id == conversation_id,
                ChatbotConversation.user_id == user_id,
            )
            .order_by(
                desc(ChatbotConversationSummary.summary_version),
                desc(ChatbotConversationSummary.updated_at),
                desc(ChatbotConversationSummary.id),
            )
            .limit(1)
        )
        return self._conversation_repo._summary_record_from_model(model) if model is not None else None

    def _load_latest_pending_summary(
        self,
        session: Session,
        user_id: str,
        conversation_id: str,
    ) -> ConversationSummaryRecord | None:
        model = session.scalar(
            select(ChatbotConversationSummary)
            .join(ChatbotConversation, ChatbotConversation.id == ChatbotConversationSummary.conversation_id)
            .where(
                ChatbotConversationSummary.conversation_id == conversation_id,
                ChatbotConversation.user_id == user_id,
                ChatbotConversationSummary.status == "pending",
            )
            .order_by(
                desc(ChatbotConversationSummary.summary_version),
                desc(ChatbotConversationSummary.updated_at),
                desc(ChatbotConversationSummary.id),
            )
            .limit(1)
        )
        return self._conversation_repo._summary_record_from_model(model) if model is not None else None

    def _load_owned_summary(
        self,
        session: Session,
        summary_id: str,
        user_id: str,
    ) -> ChatbotConversationSummary | None:
        model = session.scalar(
            select(ChatbotConversationSummary)
            .join(ChatbotConversation, ChatbotConversation.id == ChatbotConversationSummary.conversation_id)
            .where(
                ChatbotConversationSummary.id == summary_id,
                ChatbotConversation.user_id == user_id,
            )
        )
        return model

    def _latest_completed_sequence(
        self,
        session: Session,
        user_id: str,
        conversation_id: str,
    ) -> int | None:
        value = session.scalar(
            select(func.max(ChatbotMessage.sequence_number))
            .where(
                ChatbotMessage.conversation_id == conversation_id,
                ChatbotMessage.user_id == user_id,
                ChatbotMessage.status == "completed",
            )
        )
        return int(value) if isinstance(value, int) else None

    def _completed_message_count(
        self,
        session: Session,
        user_id: str,
        conversation_id: str,
        after_sequence: int,
    ) -> int:
        value = session.scalar(
            select(func.count())
            .select_from(ChatbotMessage)
            .where(
                ChatbotMessage.conversation_id == conversation_id,
                ChatbotMessage.user_id == user_id,
                ChatbotMessage.status == "completed",
                ChatbotMessage.sequence_number > after_sequence,
            )
        )
        return int(value or 0)

    def _completed_token_count(
        self,
        session: Session,
        user_id: str,
        conversation_id: str,
        after_sequence: int,
    ) -> int:
        value = session.scalar(
            select(func.coalesce(func.sum(ChatbotMessage.total_tokens), 0))
            .where(
                ChatbotMessage.conversation_id == conversation_id,
                ChatbotMessage.user_id == user_id,
                ChatbotMessage.status == "completed",
                ChatbotMessage.sequence_number > after_sequence,
            )
        )
        return int(value or 0)

    def _load_source_messages(
        self,
        session: Session,
        user_id: str,
        conversation_id: str,
        *,
        start_sequence: int,
        end_sequence: int,
    ) -> Iterator[LLMMessage]:
        stmt = (
            select(ChatbotMessage)
            .where(
                ChatbotMessage.conversation_id == conversation_id,
                ChatbotMessage.user_id == user_id,
                ChatbotMessage.status == "completed",
                ChatbotMessage.role.in_(("user", "assistant")),
                ChatbotMessage.sequence_number >= start_sequence,
                ChatbotMessage.sequence_number <= end_sequence,
            )
            .order_by(ChatbotMessage.sequence_number.asc(), ChatbotMessage.id.asc())
        )
        for row in session.scalars(stmt):
            yield LLMMessage(role=row.role, content=row.content)

    @staticmethod
    def _render_source_messages(
        source_messages: tuple[LLMMessage, ...],
        *,
        window: SummaryWindow,
        previous_summary: str | None,
    ) -> str:
        lines = [
            "Update the cumulative conversation summary.",
            f"Summary window: messages {window.start_sequence}-{window.end_sequence}.",
        ]
        if previous_summary:
            lines.append("Previous summary:")
            lines.append(previous_summary)
        lines.append("Source messages:")
        for message in source_messages:
            lines.append(f"{message.role}: {message.content}")
        lines.append("Return a concise cumulative summary in Chinese or English as appropriate.")
        return "\n".join(lines)

    @staticmethod
    def _build_system_prompt() -> str:
        return (
            "You are the summarization layer for the chatbot.\n"
            "Preserve user preferences, project context, open questions, and decisions.\n"
            "Do not invent facts. Update the cumulative conversation summary only."
        )

    @staticmethod
    def _usage_counts(usage: Any | None) -> tuple[int, int, int]:
        if usage is None:
            return 0, 0, 0
        return usage.prompt_tokens, usage.completion_tokens, usage.total_tokens

    @staticmethod
    def _normalize_uuid(value: str, *, field_name: str) -> str:
        try:
            return str(UUID(str(value)))
        except Exception as exc:  # pragma: no cover - defensive
            raise ValueError(f"{field_name} must be a UUID") from exc

    @contextmanager
    def _session(self) -> Iterator[Session]:
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
