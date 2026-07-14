from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from queue import Empty, Full, Queue
from threading import Event, Lock, Thread
from typing import Iterator, Sequence
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.errors import ChatbotApiError
from app.chatbot.llm.client import LLMClient
from app.chatbot.memory.memory_extractor import MemoryDraft, MemoryExtractor, build_memory_hash, normalize_memory_content
from app.chatbot.memory.semantic_memory import SemanticMemoryIndex
from app.chatbot.models.conversation import ChatbotConversation
from app.chatbot.models.memory import ChatbotMemory
from app.chatbot.models.message import ChatbotMessage
from app.chatbot.repositories.cursor import MemoryCursor, decode_memory_cursor
from app.chatbot.repositories.memory_repository import MemoryPage, MemoryRecord, MemoryRepository
from app.chatbot.repositories.job_repository import JobRepository
from app.chatbot.observability import log_chatbot_event
from app.chatbot.schemas.common import DeleteResultData
from app.chatbot.schemas.memory import MemoryData, MemoryPageData, MemoryUpdateRequest
from app.core.config import Settings, get_settings
from app.db.session import build_session_factory


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class _WorkItem:
    user_id: str
    conversation_id: str
    user_message_id: str
    assistant_message_id: str
    source_message_ids: tuple[str, ...]


class MemoryService:
    def __init__(
        self,
        session_factory: sessionmaker[Session] | None = None,
        *,
        extractor: MemoryExtractor | None = None,
        llm_client: LLMClient | None = None,
        settings: Settings | None = None,
        repository: MemoryRepository | None = None,
        semantic_index: SemanticMemoryIndex | None = None,
        job_repository: JobRepository | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.session_factory = session_factory or build_session_factory(self.settings)
        self.repository = repository or MemoryRepository(self.session_factory)
        self.extractor = extractor or MemoryExtractor(llm_client=llm_client, settings=self.settings)
        self.semantic_index = semantic_index
        if self.semantic_index is None and self.settings.chatbot_semantic_memory_enabled:
            self.semantic_index = SemanticMemoryIndex(settings=self.settings)
        self._queue: Queue[_WorkItem | None] = Queue(maxsize=100)
        self._worker_started = False
        self._worker_lock = Lock()
        self._stop_event = Event()
        self.job_repository = job_repository or JobRepository(self.session_factory)

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

    @staticmethod
    def _memory_data(record: MemoryRecord) -> MemoryData:
        return MemoryData(
            id=record.id,
            conversation_id=record.conversation_id,
            memory_type=record.memory_type,
            content=record.content,
            importance=record.importance,
            confidence=record.confidence,
            source_message_ids=record.source_message_ids,
            status=record.status,
            last_accessed_at=record.last_accessed_at,
            expires_at=record.expires_at,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def _ensure_worker(self) -> None:
        if self._worker_started:
            return
        with self._worker_lock:
            if self._worker_started:
                return
            thread = Thread(target=self._worker_loop, name="chatbot-memory-worker", daemon=True)
            thread.start()
            self._worker_started = True

    def _worker_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                item = self._queue.get(timeout=0.5)
            except Empty:
                continue
            if item is None:
                return
            try:
                self.process_completed_turn(
                    item.user_id,
                    item.conversation_id,
                    item.user_message_id,
                    item.assistant_message_id,
                    source_message_ids=list(item.source_message_ids),
                )
            except Exception:
                continue

    def _sync_semantic_upsert(self, record: MemoryRecord) -> None:
        if self.semantic_index is None or not self.semantic_index.enabled:
            return
        try:
            self.semantic_index.upsert_memory(record)
        except Exception:
            log_chatbot_event(
                "chatbot.semantic.degraded",
                user_id=record.user_id,
                conversation_id=record.conversation_id,
                message_id=record.id,
                status="upsert_failed",
                source="semantic_index",
                reason="upsert",
            )
            self.repository.update(record.id, record.user_id, embedding_status="failed")
            return
        self.repository.update(record.id, record.user_id, embedding_status="indexed")

    def _sync_semantic_delete(self, memory_id: str, user_id: str) -> None:
        if self.semantic_index is None or not self.semantic_index.enabled:
            return
        try:
            self.semantic_index.delete_memory(memory_id)
        except Exception:
            log_chatbot_event(
                "chatbot.semantic.degraded",
                user_id=user_id,
                message_id=memory_id,
                status="delete_failed",
                source="semantic_index",
                reason="delete",
            )
            return

    def submit_completed_turn(
        self,
        user_id: str,
        conversation_id: str,
        user_message_id: str,
        assistant_message_id: str,
        *,
        source_message_ids: Sequence[str] | None = None,
    ) -> None:
        if not self.settings.chatbot_long_term_memory_enabled:
            return
        self._ensure_worker()
        item = _WorkItem(
            user_id=user_id,
            conversation_id=conversation_id,
            user_message_id=user_message_id,
            assistant_message_id=assistant_message_id,
            source_message_ids=tuple(source_message_ids or (user_message_id, assistant_message_id)),
        )
        try:
            self._queue.put_nowait(item)
        except Full:
            return

    def _validate_turn_sources(
        self,
        session: Session,
        user_id: str,
        conversation_id: str,
        source_message_ids: Sequence[str],
    ) -> tuple[ChatbotMessage, ChatbotMessage]:
        if len(source_message_ids) < 2:
            raise ChatbotApiError(
                status_code=404,
                code="CHATBOT_MESSAGE_NOT_FOUND",
                message="Source messages not found",
            )

        rows = list(
            session.scalars(
                select(ChatbotMessage).where(
                    ChatbotMessage.user_id == user_id,
                    ChatbotMessage.conversation_id == conversation_id,
                    ChatbotMessage.id.in_(list(source_message_ids)),
                )
            )
        )
        if len(rows) != len(set(source_message_ids)):
            raise ChatbotApiError(
                status_code=404,
                code="CHATBOT_MESSAGE_NOT_FOUND",
                message="Source messages not found",
            )

        by_id = {row.id: row for row in rows}
        user_message = by_id.get(str(source_message_ids[0]))
        assistant_message = by_id.get(str(source_message_ids[1]))
        if (
            user_message is None
            or assistant_message is None
            or user_message.role != "user"
            or assistant_message.role != "assistant"
        ):
            raise ChatbotApiError(
                status_code=404,
                code="CHATBOT_MESSAGE_NOT_FOUND",
                message="Source messages not found",
            )
        return user_message, assistant_message

    def _supersede_active_memories(
        self,
        user_id: str,
        memory_type: str,
        *,
        exclude_memory_id: str | None = None,
    ) -> list[MemoryRecord]:
        superseded: list[MemoryRecord] = []
        with self._session() as session:
            stmt = (
                session.query(ChatbotMemory)
                .filter(
                    ChatbotMemory.user_id == user_id,
                    ChatbotMemory.memory_type == memory_type,
                    ChatbotMemory.status == "active",
                    ChatbotMemory.deleted_at.is_(None),
                )
            )
            if exclude_memory_id is not None:
                stmt = stmt.filter(ChatbotMemory.id != exclude_memory_id)
            for row in stmt.all():
                row.status = "superseded"
                row.embedding_status = "deleted"
                row.updated_at = _utcnow()
                superseded.append(MemoryRepository._record_from_model(row))
        return superseded

    def _upsert_draft(self, user_id: str, draft: MemoryDraft, conversation_id: str) -> MemoryRecord | None:
        existing = self.repository.get_by_normalized_hash(user_id, draft.normalized_hash)
        target_status = "active" if draft.confidence >= self.settings.chatbot_memory_min_confidence else "candidate"

        if draft.action == "forget":
            target_hash = draft.target_hash or draft.normalized_hash
            target = self.repository.get_by_normalized_hash(user_id, target_hash)
            if target is None:
                return None
            deleted = self.repository.soft_delete(target.id, user_id)
            if deleted is not None:
                self._sync_semantic_delete(deleted.id, deleted.user_id)
            return deleted

        if existing is not None and existing.status in {"candidate", "active"}:
            if existing.status == "candidate" and target_status == "active":
                updated = self.repository.update(
                    existing.id,
                    user_id,
                    content=draft.content,
                    normalized_hash=draft.normalized_hash,
                    status="active",
                    importance=draft.importance,
                    confidence=draft.confidence,
                    source_message_ids=list(draft.source_message_ids),
                    conversation_id=conversation_id,
                    embedding_status="pending",
                )
                if updated is not None and updated.status == "active":
                    superseded = self._supersede_active_memories(user_id, draft.memory_type, exclude_memory_id=updated.id)
                    for superseded_record in superseded:
                        self._sync_semantic_delete(superseded_record.id, superseded_record.user_id)
                    self._sync_semantic_upsert(updated)
                return updated
            if existing.status == "active" and target_status != "active":
                updated = self.repository.update(
                    existing.id,
                    user_id,
                    content=draft.content,
                    normalized_hash=draft.normalized_hash,
                    status=target_status,
                    importance=draft.importance,
                    confidence=draft.confidence,
                    source_message_ids=list(draft.source_message_ids),
                    conversation_id=conversation_id,
                    embedding_status="deleted",
                )
                if updated is not None:
                    self._sync_semantic_delete(updated.id, updated.user_id)
                return updated or existing
            if existing.status == "active" and target_status == "active":
                self._sync_semantic_upsert(existing)
                return existing
            return existing

        if target_status == "active":
            superseded = self._supersede_active_memories(user_id, draft.memory_type)
            for superseded_record in superseded:
                self._sync_semantic_delete(superseded_record.id, superseded_record.user_id)

        record = self.repository.create(
            user_id,
            memory_type=draft.memory_type,
            content=draft.content,
            normalized_hash=draft.normalized_hash,
            conversation_id=conversation_id,
            importance=draft.importance,
            confidence=draft.confidence,
            source_message_ids=list(draft.source_message_ids),
            status=target_status,
            embedding_status="pending",
        )
        if record.status == "active":
            self._sync_semantic_upsert(record)
        return record

    def process_completed_turn(
        self,
        user_id: str,
        conversation_id: str,
        user_message_id: str,
        assistant_message_id: str,
        *,
        source_message_ids: Sequence[str] | None = None,
    ) -> list[MemoryRecord]:
        normalized_user_id = str(UUID(user_id))
        normalized_conversation_id = str(UUID(conversation_id))
        normalized_user_message_id = str(UUID(user_message_id))
        normalized_assistant_message_id = str(UUID(assistant_message_id))
        source_ids = [str(UUID(source_id)) for source_id in (source_message_ids or [normalized_user_message_id, normalized_assistant_message_id])]

        with self._session() as session:
            user_message, assistant_message = self._validate_turn_sources(
                session,
                normalized_user_id,
                normalized_conversation_id,
                source_ids,
            )
            conversation = session.scalar(
                select(ChatbotConversation).where(
                    ChatbotConversation.id == normalized_conversation_id,
                    ChatbotConversation.user_id == normalized_user_id,
                    ChatbotConversation.deleted_at.is_(None),
                )
            )
            if conversation is None:
                raise ChatbotApiError(
                    status_code=404,
                    code="CHATBOT_CONVERSATION_NOT_FOUND",
                    message="Conversation not found",
                )
            user_text = user_message.content
            assistant_text = assistant_message.content

        try:
            drafts = self.extractor.extract(
                user_message=user_text,
                assistant_message=assistant_text,
                user_id=normalized_user_id,
                conversation_id=normalized_conversation_id,
                source_message_ids=source_ids,
            )
        except Exception:
            failed = self.repository.create(
                normalized_user_id,
                memory_type="explicit",
                content=user_text[:4000],
                normalized_hash=build_memory_hash("explicit", normalize_memory_content(user_text[:4000])),
                conversation_id=normalized_conversation_id,
                importance=0.0,
                confidence=0.0,
                source_message_ids=source_ids,
                status="failed",
                embedding_status="failed",
            )
            return [failed]
        created: list[MemoryRecord] = []
        for draft in drafts:
            record = self._upsert_draft(normalized_user_id, draft, normalized_conversation_id)
            if record is not None:
                created.append(record)
        return created

    def list_memories(
        self,
        session: Session,
        user_id: str,
        *,
        status: str | None = "active",
        memory_type: str | None = None,
        conversation_id: str | None = None,
        limit: int = 20,
        cursor: str | None = None,
    ) -> MemoryPageData:
        try:
            page = self.repository.list_owned_page(
                user_id,
                status=status,
                memory_type=memory_type,
                conversation_id=conversation_id,
                cursor=cursor,
                limit=limit,
            )
        except ValueError as exc:
            raise ChatbotApiError(
                status_code=400,
                code="CHATBOT_INVALID_CURSOR",
                message="Invalid memory cursor",
            ) from exc
        return MemoryPageData(
            items=[self._memory_data(record) for record in page.items],
            next_cursor=page.next_cursor,
            has_more=page.has_more,
        )

    def get_memory(self, session: Session, user_id: str, memory_id: str) -> MemoryData:
        record = self.repository.get_owned(memory_id, user_id)
        if record is None:
            raise ChatbotApiError(
                status_code=404,
                code="CHATBOT_MEMORY_NOT_FOUND",
                message="Memory not found",
            )
        return self._memory_data(record)

    def update_memory(
        self,
        session: Session,
        user_id: str,
        memory_id: str,
        request: MemoryUpdateRequest,
    ) -> MemoryData:
        record = self.repository.get_owned(memory_id, user_id)
        if record is None:
            raise ChatbotApiError(
                status_code=404,
                code="CHATBOT_MEMORY_NOT_FOUND",
                message="Memory not found",
            )

        content = request.content if request.content is not None else record.content
        normalized_content = normalize_memory_content(content)
        normalized_hash = build_memory_hash(record.memory_type, normalized_content)
        status = request.status or record.status
        if status == "active":
            conflict = self.repository.get_latest_active_by_type(user_id, record.memory_type)
            if conflict is not None and conflict.id != record.id and conflict.normalized_hash != normalized_hash:
                raise ChatbotApiError(
                    status_code=409,
                    code="CHATBOT_MEMORY_CONFLICT",
                    message="Active memory conflict",
                    details={"memory_id": conflict.id},
                )

        updated = self.repository.update(
            record.id,
            user_id,
            content=content if request.content is not None else None,
            normalized_hash=normalized_hash if request.content is not None else None,
            status=status,
            expires_at=request.expires_at,
            embedding_status="pending" if request.content is not None else None,
        )
        if updated is None:
            raise ChatbotApiError(
                status_code=404,
                code="CHATBOT_MEMORY_NOT_FOUND",
                message="Memory not found",
            )
        if updated.status == "active":
            self._sync_semantic_upsert(updated)
        elif record.status == "active" and updated.status != "active":
            self._sync_semantic_delete(updated.id, updated.user_id)
        return self._memory_data(updated)

    def delete_memory(self, session: Session, user_id: str, memory_id: str) -> DeleteResultData:
        row = session.scalar(
            select(ChatbotMemory)
            .where(
                ChatbotMemory.id == memory_id,
                ChatbotMemory.user_id == user_id,
                ChatbotMemory.deleted_at.is_(None),
            )
            .with_for_update()
        )
        if row is None:
            raise ChatbotApiError(
                status_code=404,
                code="CHATBOT_MEMORY_NOT_FOUND",
                message="Memory not found",
            )
        now = _utcnow()
        row.status = "deleted"
        row.embedding_status = "deleted"
        row.deleted_at = now
        row.updated_at = now
        self.job_repository.enqueue(
            session,
            kind="cleanup_memory",
            dedup_key=f"cleanup-memory:{row.id}",
            payload={"user_id": user_id, "memory_id": row.id},
        )
        session.commit()
        return DeleteResultData(id=row.id, status="deleted", cleanup_status="pending")


_MEMORY_SERVICE: MemoryService | None = None


def get_memory_service() -> MemoryService:
    global _MEMORY_SERVICE
    if _MEMORY_SERVICE is None:
        _MEMORY_SERVICE = MemoryService()
    return _MEMORY_SERVICE
