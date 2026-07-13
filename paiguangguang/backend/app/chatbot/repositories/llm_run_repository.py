from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator

from sqlalchemy import desc, select, update
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.models.conversation import ChatbotConversation
from app.chatbot.models.llm_run import ChatbotLLMRun


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class LLMRunRecord:
    id: str
    request_id: str
    user_id: str
    conversation_id: str
    message_id: str
    provider: str
    model: str
    prompt_version: str
    status: str
    attempt_count: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: int | None
    first_token_latency_ms: int | None
    finish_reason: str | None
    error_code: str | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class LLMRunRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    @contextmanager
    def _session(self) -> Iterator[Session]:
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    def _record_from_model(model: ChatbotLLMRun) -> LLMRunRecord:
        return LLMRunRecord(
            id=model.id,
            request_id=model.request_id,
            user_id=model.user_id,
            conversation_id=model.conversation_id,
            message_id=model.message_id,
            provider=model.provider,
            model=model.model,
            prompt_version=model.prompt_version,
            status=model.status,
            attempt_count=model.attempt_count,
            prompt_tokens=model.prompt_tokens,
            completion_tokens=model.completion_tokens,
            total_tokens=model.total_tokens,
            latency_ms=model.latency_ms,
            first_token_latency_ms=model.first_token_latency_ms,
            finish_reason=model.finish_reason,
            error_code=model.error_code,
            error_message=model.error_message,
            started_at=model.started_at,
            completed_at=model.completed_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def create(
        self,
        *,
        request_id: str,
        user_id: str,
        conversation_id: str,
        message_id: str,
        provider: str,
        model: str,
        prompt_version: str,
        attempt_count: int = 1,
    ) -> LLMRunRecord:
        now = _utcnow()
        with self._session() as session:
            conversation = session.scalar(
                select(ChatbotConversation)
                .where(
                    ChatbotConversation.id == conversation_id,
                    ChatbotConversation.user_id == user_id,
                    ChatbotConversation.deleted_at.is_(None),
                )
                .with_for_update()
            )
            if conversation is None:
                raise ValueError("Conversation not found")

            row = ChatbotLLMRun(
                request_id=request_id,
                user_id=user_id,
                conversation_id=conversation_id,
                message_id=message_id,
                provider=provider,
                model=model,
                prompt_version=prompt_version,
                status="pending",
                attempt_count=attempt_count,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                latency_ms=None,
                first_token_latency_ms=None,
                finish_reason=None,
                error_code=None,
                error_message=None,
                started_at=None,
                completed_at=None,
                created_at=now,
                updated_at=now,
            )
            session.add(row)
            session.flush()
            session.refresh(row)
            return self._record_from_model(row)

    def get_owned(self, run_id: str, user_id: str) -> LLMRunRecord | None:
        with self._session() as session:
            model = session.scalar(
                select(ChatbotLLMRun).where(
                    ChatbotLLMRun.id == run_id,
                    ChatbotLLMRun.user_id == user_id,
                )
            )
            return self._record_from_model(model) if model is not None else None

    def get_active_for_conversation(self, conversation_id: str, user_id: str) -> LLMRunRecord | None:
        with self._session() as session:
            model = session.scalar(
                select(ChatbotLLMRun)
                .where(
                    ChatbotLLMRun.conversation_id == conversation_id,
                    ChatbotLLMRun.user_id == user_id,
                    ChatbotLLMRun.status.in_(("pending", "streaming")),
                )
                .order_by(desc(ChatbotLLMRun.updated_at), desc(ChatbotLLMRun.id))
                .limit(1)
            )
            return self._record_from_model(model) if model is not None else None

    def mark_streaming(
        self,
        run_id: str,
        user_id: str,
        *,
        expected_status: str,
        first_token_latency_ms: int | None = None,
        started_at: datetime | None = None,
    ) -> LLMRunRecord | None:
        now = _utcnow()
        updates: dict[str, object] = {
            "status": "streaming",
            "updated_at": now,
        }
        if first_token_latency_ms is not None:
            updates["first_token_latency_ms"] = first_token_latency_ms
        if started_at is not None:
            updates["started_at"] = started_at
        else:
            updates["started_at"] = now

        with self._session() as session:
            result = session.execute(
                update(ChatbotLLMRun)
                .where(
                    ChatbotLLMRun.id == run_id,
                    ChatbotLLMRun.user_id == user_id,
                    ChatbotLLMRun.status == expected_status,
                )
                .values(**updates)
            )
            if result.rowcount == 0:
                return None
            model = session.scalar(select(ChatbotLLMRun).where(ChatbotLLMRun.id == run_id, ChatbotLLMRun.user_id == user_id))
            return self._record_from_model(model) if model is not None else None

    def finalize(
        self,
        run_id: str,
        user_id: str,
        *,
        expected_status: str,
        status: str,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        total_tokens: int | None = None,
        latency_ms: int | None = None,
        first_token_latency_ms: int | None = None,
        finish_reason: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        completed_at: datetime | None = None,
    ) -> LLMRunRecord | None:
        if status not in {"completed", "failed", "cancelled"}:
            raise ValueError("status must be terminal")

        now = _utcnow()
        updates: dict[str, object] = {
            "status": status,
            "completed_at": completed_at or now,
            "updated_at": now,
        }
        if prompt_tokens is not None:
            updates["prompt_tokens"] = prompt_tokens
        if completion_tokens is not None:
            updates["completion_tokens"] = completion_tokens
        if total_tokens is not None:
            updates["total_tokens"] = total_tokens
        if latency_ms is not None:
            updates["latency_ms"] = latency_ms
        if first_token_latency_ms is not None:
            updates["first_token_latency_ms"] = first_token_latency_ms
        if finish_reason is not None:
            updates["finish_reason"] = finish_reason
        if error_code is not None:
            updates["error_code"] = error_code
        if error_message is not None:
            updates["error_message"] = error_message

        with self._session() as session:
            result = session.execute(
                update(ChatbotLLMRun)
                .where(
                    ChatbotLLMRun.id == run_id,
                    ChatbotLLMRun.user_id == user_id,
                    ChatbotLLMRun.status == expected_status,
                )
                .values(**updates)
            )
            if result.rowcount == 0:
                return None
            model = session.scalar(select(ChatbotLLMRun).where(ChatbotLLMRun.id == run_id, ChatbotLLMRun.user_id == user_id))
            return self._record_from_model(model) if model is not None else None

    def scan_stale_runs(self, older_than: datetime, *, limit: int = 100) -> list[LLMRunRecord]:
        if limit < 1:
            raise ValueError("limit must be positive")

        with self._session() as session:
            rows = list(
                session.scalars(
                    select(ChatbotLLMRun)
                    .where(
                        ChatbotLLMRun.status.in_(("pending", "streaming")),
                        ChatbotLLMRun.updated_at < older_than,
                    )
                    .order_by(ChatbotLLMRun.updated_at.asc(), ChatbotLLMRun.id.asc())
                    .limit(limit)
                )
            )
        return [self._record_from_model(row) for row in rows]

