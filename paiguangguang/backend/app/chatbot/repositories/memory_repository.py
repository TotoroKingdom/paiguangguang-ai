from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator

from sqlalchemy import and_, desc, or_, select, update
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.models.memory import ChatbotMemory
from app.chatbot.repositories.cursor import MemoryCursor, MemoryCursorError, encode_memory_cursor


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class MemoryRecord:
    id: str
    user_id: str
    conversation_id: str | None
    memory_type: str
    content: str
    importance: float
    confidence: float
    source_message_ids: list[str]
    status: str
    last_accessed_at: datetime | None
    expires_at: datetime | None
    normalized_hash: str
    embedding_status: str
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class MemoryPage:
    items: list[MemoryRecord]
    next_cursor: str | None
    has_more: bool


class MemoryRepository:
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
    def _record_from_model(model: ChatbotMemory) -> MemoryRecord:
        return MemoryRecord(
            id=model.id,
            user_id=model.user_id,
            conversation_id=model.conversation_id,
            memory_type=model.memory_type,
            content=model.content,
            importance=model.importance,
            confidence=model.confidence,
            source_message_ids=list(model.source_message_ids or []),
            status=model.status,
            last_accessed_at=model.last_accessed_at,
            expires_at=model.expires_at,
            normalized_hash=model.normalized_hash,
            embedding_status=model.embedding_status,
            deleted_at=model.deleted_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def get_owned(self, memory_id: str, user_id: str, *, include_deleted: bool = False) -> MemoryRecord | None:
        with self._session() as session:
            stmt = select(ChatbotMemory).where(
                ChatbotMemory.id == memory_id,
                ChatbotMemory.user_id == user_id,
            )
            if not include_deleted:
                stmt = stmt.where(ChatbotMemory.deleted_at.is_(None), ChatbotMemory.status != "deleted")
            model = session.scalar(stmt)
            return self._record_from_model(model) if model is not None else None

    def get_by_normalized_hash(
        self,
        user_id: str,
        normalized_hash: str,
        *,
        include_deleted: bool = False,
    ) -> MemoryRecord | None:
        with self._session() as session:
            stmt = select(ChatbotMemory).where(
                ChatbotMemory.user_id == user_id,
                ChatbotMemory.normalized_hash == normalized_hash,
            )
            if not include_deleted:
                stmt = stmt.where(ChatbotMemory.deleted_at.is_(None), ChatbotMemory.status != "deleted")
            model = session.scalar(stmt)
            return self._record_from_model(model) if model is not None else None

    def get_latest_active_by_type(self, user_id: str, memory_type: str) -> MemoryRecord | None:
        with self._session() as session:
            model = session.scalar(
                select(ChatbotMemory)
                .where(
                    ChatbotMemory.user_id == user_id,
                    ChatbotMemory.memory_type == memory_type,
                    ChatbotMemory.status == "active",
                    ChatbotMemory.deleted_at.is_(None),
                )
                .order_by(desc(ChatbotMemory.updated_at), desc(ChatbotMemory.id))
                .limit(1)
            )
            return self._record_from_model(model) if model is not None else None

    def create(
        self,
        user_id: str,
        *,
        memory_type: str,
        content: str,
        normalized_hash: str,
        conversation_id: str | None = None,
        importance: float = 0.0,
        confidence: float = 0.0,
        source_message_ids: list[str] | None = None,
        status: str = "candidate",
        embedding_status: str = "pending",
        expires_at: datetime | None = None,
    ) -> MemoryRecord:
        existing = self.get_by_normalized_hash(user_id, normalized_hash)
        if existing is not None and existing.status in {"candidate", "active"}:
            return existing

        now = _utcnow()
        with self._session() as session:
            row = ChatbotMemory(
                user_id=user_id,
                conversation_id=conversation_id,
                memory_type=memory_type,
                content=content,
                importance=importance,
                confidence=confidence,
                source_message_ids=list(source_message_ids or []),
                status=status,
                last_accessed_at=None,
                expires_at=expires_at,
                normalized_hash=normalized_hash,
                embedding_status=embedding_status,
                deleted_at=None,
                created_at=now,
                updated_at=now,
            )
            session.add(row)
            session.flush()
            session.refresh(row)
            return self._record_from_model(row)

    def update(
        self,
        memory_id: str,
        user_id: str,
        *,
        content: str | None = None,
        normalized_hash: str | None = None,
        status: str | None = None,
        importance: float | None = None,
        confidence: float | None = None,
        source_message_ids: list[str] | None = None,
        expires_at: datetime | None = None,
        embedding_status: str | None = None,
        conversation_id: str | None = None,
    ) -> MemoryRecord | None:
        updates: dict[str, object] = {"updated_at": _utcnow()}
        if content is not None:
            updates["content"] = content
        if normalized_hash is not None:
            updates["normalized_hash"] = normalized_hash
        if status is not None:
            updates["status"] = status
        if importance is not None:
            updates["importance"] = importance
        if confidence is not None:
            updates["confidence"] = confidence
        if source_message_ids is not None:
            updates["source_message_ids"] = list(source_message_ids)
        if expires_at is not None:
            updates["expires_at"] = expires_at
        if embedding_status is not None:
            updates["embedding_status"] = embedding_status
        if conversation_id is not None:
            updates["conversation_id"] = conversation_id

        with self._session() as session:
            result = session.execute(
                update(ChatbotMemory)
                .where(
                    ChatbotMemory.id == memory_id,
                    ChatbotMemory.user_id == user_id,
                    ChatbotMemory.deleted_at.is_(None),
                )
                .values(**updates)
            )
            if result.rowcount == 0:
                return None
            model = session.scalar(select(ChatbotMemory).where(ChatbotMemory.id == memory_id, ChatbotMemory.user_id == user_id))
            return self._record_from_model(model) if model is not None else None

    def list_owned(
        self,
        user_id: str,
        status: str | None = "active",
        *,
        memory_type: str | None = None,
        conversation_id: str | None = None,
        cursor: str | MemoryCursor | None = None,
        include_expired: bool = False,
        limit: int = 100,
    ) -> list[MemoryRecord]:
        return self.list_owned_page(
            user_id,
            status=status,
            memory_type=memory_type,
            conversation_id=conversation_id,
            cursor=cursor,
            include_expired=include_expired,
            limit=limit,
        ).items

    def list_owned_page(
        self,
        user_id: str,
        status: str | None = "active",
        *,
        memory_type: str | None = None,
        conversation_id: str | None = None,
        cursor: str | MemoryCursor | None = None,
        include_expired: bool = False,
        limit: int = 100,
    ) -> MemoryPage:
        if limit < 1 or limit > 100:
            raise ValueError("limit must be positive and no greater than 100")
        if status == "deleted":
            raise ValueError("deleted memories are not listable")
        if status is not None and status not in {"candidate", "active", "superseded", "failed"}:
            raise ValueError("Invalid memory status")

        position: MemoryCursor | None = None
        if isinstance(cursor, str):
            from app.chatbot.repositories.cursor import decode_memory_cursor

            try:
                position = decode_memory_cursor(
                    cursor,
                    expected_status_filter=status,
                    expected_memory_type_filter=memory_type,
                    expected_conversation_id_filter=conversation_id,
                )
            except MemoryCursorError as exc:
                raise ValueError("Invalid memory cursor") from exc
        elif isinstance(cursor, MemoryCursor):
            if (
                cursor.status_filter != status
                or cursor.memory_type_filter != memory_type
                or cursor.conversation_id_filter != conversation_id
            ):
                raise ValueError("Invalid memory cursor")
            position = cursor

        now = _utcnow()
        with self._session() as session:
            stmt = select(ChatbotMemory).where(
                ChatbotMemory.user_id == user_id,
                ChatbotMemory.deleted_at.is_(None),
            )
            if status is None:
                stmt = stmt.where(ChatbotMemory.status.in_(("candidate", "active", "superseded")))
            else:
                stmt = stmt.where(ChatbotMemory.status == status)
            if memory_type is not None:
                stmt = stmt.where(ChatbotMemory.memory_type == memory_type)
            if conversation_id is not None:
                stmt = stmt.where(ChatbotMemory.conversation_id == conversation_id)
            if not include_expired:
                stmt = stmt.where((ChatbotMemory.expires_at.is_(None)) | (ChatbotMemory.expires_at > now))
            if position is not None:
                stmt = stmt.where(
                    or_(
                        ChatbotMemory.updated_at < position.updated_at,
                        and_(
                            ChatbotMemory.updated_at == position.updated_at,
                            ChatbotMemory.id < position.memory_id,
                        ),
                    )
                )
            stmt = stmt.order_by(desc(ChatbotMemory.updated_at), desc(ChatbotMemory.id)).limit(limit + 1)
            rows = list(session.scalars(stmt))

        has_more = len(rows) > limit
        visible_rows = rows[:limit]
        items = [self._record_from_model(row) for row in visible_rows]
        next_cursor = None
        if has_more and visible_rows:
            tail = visible_rows[-1]
            next_cursor = encode_memory_cursor(
                MemoryCursor(
                    updated_at=tail.updated_at,
                    memory_id=tail.id,
                    status_filter=status,
                    memory_type_filter=memory_type,
                    conversation_id_filter=conversation_id,
                )
            )
        return MemoryPage(items=items, next_cursor=next_cursor, has_more=has_more)

    def claim_embedding_backlog(self, user_id: str, *, limit: int = 20) -> list[MemoryRecord]:
        if limit < 1:
            raise ValueError("limit must be positive")

        with self._session() as session:
            stmt = (
                select(ChatbotMemory)
                .where(
                    ChatbotMemory.user_id == user_id,
                    ChatbotMemory.deleted_at.is_(None),
                    ChatbotMemory.embedding_status == "pending",
                )
                .order_by(desc(ChatbotMemory.updated_at), desc(ChatbotMemory.id))
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
            rows = list(session.scalars(stmt))
        return [self._record_from_model(row) for row in rows]

    def soft_delete(self, memory_id: str, user_id: str) -> MemoryRecord | None:
        now = _utcnow()
        with self._session() as session:
            result = session.execute(
                update(ChatbotMemory)
                .where(
                    ChatbotMemory.id == memory_id,
                    ChatbotMemory.user_id == user_id,
                    ChatbotMemory.deleted_at.is_(None),
                )
                .values(
                    status="deleted",
                    embedding_status="deleted",
                    deleted_at=now,
                    updated_at=now,
                )
            )
            if result.rowcount == 0:
                return None
            model = session.scalar(select(ChatbotMemory).where(ChatbotMemory.id == memory_id, ChatbotMemory.user_id == user_id))
            return self._record_from_model(model) if model is not None else None
