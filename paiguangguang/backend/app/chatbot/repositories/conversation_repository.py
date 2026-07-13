from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator

from sqlalchemy import and_, desc, or_, select
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.models.conversation import ChatbotConversation
from app.chatbot.repositories.cursor import ConversationCursor, ConversationCursorError, encode_conversation_cursor


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class ConversationRecord:
    id: str
    user_id: str
    title: str
    title_source: str
    status: str
    model: str
    system_prompt_version: str
    next_sequence: int
    last_message_at: datetime
    archived_at: datetime | None
    deleted_at: datetime | None
    cleanup_status: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ConversationPage:
    items: list[ConversationRecord]
    next_cursor: str | None
    has_more: bool


class ConversationRepository:
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
    def _record_from_model(model: ChatbotConversation) -> ConversationRecord:
        return ConversationRecord(
            id=model.id,
            user_id=model.user_id,
            title=model.title,
            title_source=model.title_source,
            status=model.status,
            model=model.model,
            system_prompt_version=model.system_prompt_version,
            next_sequence=model.next_sequence,
            last_message_at=model.last_message_at,
            archived_at=model.archived_at,
            deleted_at=model.deleted_at,
            cleanup_status=model.cleanup_status,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _normalize_status(status: str | None) -> str | None:
        if status is None:
            return None
        normalized = status.strip().lower()
        if normalized not in {"active", "archived", "deleted"}:
            raise ValueError("Invalid conversation status")
        return normalized

    @staticmethod
    def _build_older_than_cursor_clause(cursor: ConversationCursor):
        return or_(
            ChatbotConversation.last_message_at < cursor.last_message_at,
            and_(
                ChatbotConversation.last_message_at == cursor.last_message_at,
                ChatbotConversation.id < cursor.conversation_id,
            ),
        )

    @staticmethod
    def _build_owned_statement(
        conversation_id: str,
        user_id: str,
        *,
        include_deleted: bool = False,
        for_update: bool = False,
    ):
        stmt = select(ChatbotConversation).where(
            ChatbotConversation.id == conversation_id,
            ChatbotConversation.user_id == user_id,
        )
        if not include_deleted:
            stmt = stmt.where(ChatbotConversation.deleted_at.is_(None))
        if for_update:
            stmt = stmt.with_for_update()
        return stmt

    def create(
        self,
        user_id: str,
        title: str,
        model: str,
        *,
        system_prompt_version: str = "v1",
        title_source: str = "default",
    ) -> ConversationRecord:
        now = _utcnow()
        with self._session() as session:
            row = ChatbotConversation(
                user_id=user_id,
                title=title,
                title_source=title_source,
                status="active",
                model=model,
                system_prompt_version=system_prompt_version,
                next_sequence=1,
                last_message_at=now,
                archived_at=None,
                deleted_at=None,
                cleanup_status="pending",
                created_at=now,
                updated_at=now,
            )
            session.add(row)
            session.flush()
            session.refresh(row)
            return self._record_from_model(row)

    def get_owned(
        self,
        conversation_id: str,
        user_id: str,
        *,
        include_deleted: bool = False,
    ) -> ConversationRecord | None:
        with self._session() as session:
            stmt = self._build_owned_statement(conversation_id, user_id, include_deleted=include_deleted)
            model = session.scalar(stmt)
            if model is None:
                return None
            return self._record_from_model(model)

    def list_owned(
        self,
        user_id: str,
        status: str | None,
        position: ConversationCursor | None,
        limit: int,
    ) -> ConversationPage:
        if limit < 1:
            raise ValueError("limit must be positive")

        normalized_status = self._normalize_status(status)
        with self._session() as session:
            stmt = select(ChatbotConversation).where(ChatbotConversation.user_id == user_id)
            if normalized_status == "deleted":
                stmt = stmt.where(ChatbotConversation.status == "deleted")
            elif normalized_status is not None:
                stmt = stmt.where(
                    ChatbotConversation.status == normalized_status,
                    ChatbotConversation.deleted_at.is_(None),
                )
            else:
                stmt = stmt.where(ChatbotConversation.deleted_at.is_(None))

            if position is not None:
                if position.status_filter != normalized_status:
                    raise ConversationCursorError("Conversation cursor filter mismatch")
                stmt = stmt.where(self._build_older_than_cursor_clause(position))

            stmt = stmt.order_by(desc(ChatbotConversation.last_message_at), desc(ChatbotConversation.id)).limit(limit + 1)
            rows = list(session.scalars(stmt))

        has_more = len(rows) > limit
        visible_rows = rows[:limit]
        next_cursor = None
        if has_more and visible_rows:
            tail = visible_rows[-1]
            next_cursor = encode_conversation_cursor(
                ConversationCursor(
                    last_message_at=tail.last_message_at,
                    conversation_id=tail.id,
                    status_filter=normalized_status,
                )
            )
        return ConversationPage(
            items=[self._record_from_model(row) for row in visible_rows],
            next_cursor=next_cursor,
            has_more=has_more,
        )

    def lock_owned(
        self,
        conversation_id: str,
        user_id: str,
        *,
        include_deleted: bool = False,
    ) -> ConversationRecord | None:
        with self._session() as session:
            stmt = self._build_owned_statement(
                conversation_id,
                user_id,
                include_deleted=include_deleted,
                for_update=True,
            )
            model = session.scalar(stmt)
            if model is None:
                return None
            return self._record_from_model(model)

    def allocate_sequences(self, conversation: ChatbotConversation | ConversationRecord | str, count: int) -> list[int]:
        if count < 1:
            raise ValueError("count must be positive")

        conversation_id = (
            conversation
            if isinstance(conversation, str)
            else conversation.id
        )

        with self._session() as session:
            model = session.scalar(
                select(ChatbotConversation).where(ChatbotConversation.id == conversation_id).with_for_update()
            )
            if model is None:
                raise ValueError("Conversation not found")
            start = model.next_sequence
            model.next_sequence += count
            model.updated_at = _utcnow()
            session.flush()
            return list(range(start, start + count))
