from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import base64
import json
from typing import Iterator
from uuid import uuid4

from sqlalchemy import and_, desc, select, update
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.models.conversation import ChatbotConversation
from app.chatbot.models.message import ChatbotMessage


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MessageCursorError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class MessageCursor:
    conversation_id: str
    before_sequence_number: int
    version: int = 1


@dataclass(frozen=True, slots=True)
class MessageRecord:
    id: str
    conversation_id: str
    user_id: str
    role: str
    content: str
    content_json: dict[str, object] | None
    sequence_number: int
    status: str
    model: str | None
    parent_message_id: str | None
    client_request_id: str | None
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    error_code: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class MessagePage:
    items: list[MessageRecord]
    next_cursor: str | None
    has_more: bool


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def encode_message_cursor(cursor: MessageCursor) -> str:
    payload = {
        "v": cursor.version,
        "conversation_id": cursor.conversation_id,
        "before_sequence_number": cursor.before_sequence_number,
    }
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_message_cursor(token: str, *, expected_conversation_id: str | None = None) -> MessageCursor:
    try:
        padded = token + "=" * (-len(token) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8"))
    except Exception as exc:  # pragma: no cover - defensive
        raise MessageCursorError("Invalid message cursor") from exc

    if payload.get("v") != 1:
        raise MessageCursorError("Unsupported message cursor version")

    conversation_id = payload.get("conversation_id")
    if not isinstance(conversation_id, str) or not conversation_id:
        raise MessageCursorError("Invalid message cursor conversation_id")
    if expected_conversation_id is not None and conversation_id != expected_conversation_id:
        raise MessageCursorError("Message cursor conversation mismatch")

    before_sequence_number = payload.get("before_sequence_number")
    if not isinstance(before_sequence_number, int) or before_sequence_number < 1:
        raise MessageCursorError("Invalid message cursor sequence")

    return MessageCursor(
        conversation_id=conversation_id,
        before_sequence_number=before_sequence_number,
        version=1,
    )


class MessageRepository:
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
    def _record_from_model(model: ChatbotMessage) -> MessageRecord:
        return MessageRecord(
            id=model.id,
            conversation_id=model.conversation_id,
            user_id=model.user_id,
            role=model.role,
            content=model.content,
            content_json=model.content_json,
            sequence_number=model.sequence_number,
            status=model.status,
            model=model.model,
            parent_message_id=model.parent_message_id,
            client_request_id=model.client_request_id,
            prompt_tokens=model.prompt_tokens,
            completion_tokens=model.completion_tokens,
            total_tokens=model.total_tokens,
            error_code=model.error_code,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _build_owned_statement(
        conversation_id: str,
        user_id: str,
        *,
        before_sequence_number: int | None = None,
    ):
        stmt = select(ChatbotMessage).where(
            ChatbotMessage.conversation_id == conversation_id,
            ChatbotMessage.user_id == user_id,
        )
        if before_sequence_number is not None:
            stmt = stmt.where(ChatbotMessage.sequence_number < before_sequence_number)
        return stmt

    def create_user_and_assistant(
        self,
        conversation_id: str,
        user_id: str,
        *,
        content: str,
        client_request_id: str,
        assistant_model: str | None = None,
        assistant_content: str = "",
        assistant_status: str = "pending",
        user_content_json: dict[str, object] | None = None,
        assistant_content_json: dict[str, object] | None = None,
        parent_message_id: str | None = None,
    ) -> tuple[MessageRecord, MessageRecord]:
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

            user_sequence = conversation.next_sequence
            assistant_sequence = user_sequence + 1
            conversation.next_sequence = assistant_sequence + 1
            conversation.last_message_at = now
            conversation.updated_at = now

            user_message_id = str(uuid4())
            assistant_message_id = str(uuid4())
            user_message = ChatbotMessage(
                id=user_message_id,
                conversation_id=conversation_id,
                user_id=user_id,
                role="user",
                content=content,
                content_json=user_content_json,
                sequence_number=user_sequence,
                status="completed",
                model=None,
                parent_message_id=parent_message_id,
                client_request_id=client_request_id,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                error_code=None,
                created_at=now,
                updated_at=now,
            )
            assistant_message = ChatbotMessage(
                id=assistant_message_id,
                conversation_id=conversation_id,
                user_id=user_id,
                role="assistant",
                content=assistant_content,
                content_json=assistant_content_json,
                sequence_number=assistant_sequence,
                status=assistant_status,
                model=assistant_model,
                parent_message_id=user_message_id,
                client_request_id=None,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                error_code=None,
                created_at=now,
                updated_at=now,
            )
            session.add_all([user_message, assistant_message])
            session.flush()
            session.refresh(user_message)
            session.refresh(assistant_message)
            return self._record_from_model(user_message), self._record_from_model(assistant_message)

    def get_owned(self, message_id: str, user_id: str) -> MessageRecord | None:
        with self._session() as session:
            model = session.scalar(
                select(ChatbotMessage).where(
                    ChatbotMessage.id == message_id,
                    ChatbotMessage.user_id == user_id,
                )
            )
            return self._record_from_model(model) if model is not None else None

    def get_by_client_request_id(
        self,
        conversation_id: str,
        user_id: str,
        client_request_id: str,
    ) -> MessageRecord | None:
        with self._session() as session:
            model = session.scalar(
                select(ChatbotMessage).where(
                    ChatbotMessage.conversation_id == conversation_id,
                    ChatbotMessage.user_id == user_id,
                    ChatbotMessage.client_request_id == client_request_id,
                    ChatbotMessage.role == "user",
                )
            )
            return self._record_from_model(model) if model is not None else None

    def list_owned(
        self,
        conversation_id: str,
        user_id: str,
        before: MessageCursor | None,
        limit: int,
    ) -> MessagePage:
        if limit < 1:
            raise ValueError("limit must be positive")
        if before is not None and before.conversation_id != conversation_id:
            raise MessageCursorError("Message cursor conversation mismatch")

        with self._session() as session:
            stmt = self._build_owned_statement(
                conversation_id,
                user_id,
                before_sequence_number=before.before_sequence_number if before is not None else None,
            )
            stmt = stmt.order_by(desc(ChatbotMessage.sequence_number), desc(ChatbotMessage.id)).limit(limit + 1)
            rows = list(session.scalars(stmt))

        has_more = len(rows) > limit
        visible_rows = rows[:limit]
        visible_records = [self._record_from_model(row) for row in reversed(visible_rows)]
        next_cursor = None
        if has_more and visible_records:
            next_cursor = encode_message_cursor(
                MessageCursor(
                    conversation_id=conversation_id,
                    before_sequence_number=visible_records[0].sequence_number,
                )
            )
        return MessagePage(items=visible_records, next_cursor=next_cursor, has_more=has_more)

    def checkpoint(
        self,
        message_id: str,
        user_id: str,
        *,
        expected_status: str,
        content: str,
        content_json: dict[str, object] | None = None,
        model: str | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        total_tokens: int | None = None,
    ) -> MessageRecord | None:
        updates: dict[str, object] = {
            "content": content,
            "status": "streaming",
            "updated_at": _utcnow(),
        }
        if content_json is not None:
            updates["content_json"] = content_json
        if model is not None:
            updates["model"] = model
        if prompt_tokens is not None:
            updates["prompt_tokens"] = prompt_tokens
        if completion_tokens is not None:
            updates["completion_tokens"] = completion_tokens
        if total_tokens is not None:
            updates["total_tokens"] = total_tokens

        with self._session() as session:
            result = session.execute(
                update(ChatbotMessage)
                .where(
                    ChatbotMessage.id == message_id,
                    ChatbotMessage.user_id == user_id,
                    ChatbotMessage.status == expected_status,
                )
                .values(**updates)
            )
            if result.rowcount == 0:
                return None
            model = session.scalar(select(ChatbotMessage).where(ChatbotMessage.id == message_id, ChatbotMessage.user_id == user_id))
            return self._record_from_model(model) if model is not None else None

    def finalize(
        self,
        message_id: str,
        user_id: str,
        *,
        expected_status: str,
        status: str,
        content: str | None = None,
        content_json: dict[str, object] | None = None,
        model: str | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        total_tokens: int | None = None,
        error_code: str | None = None,
    ) -> MessageRecord | None:
        if status not in {"completed", "failed", "cancelled"}:
            raise ValueError("status must be terminal")

        updates: dict[str, object] = {
            "status": status,
            "updated_at": _utcnow(),
        }
        if content is not None:
            updates["content"] = content
        if content_json is not None:
            updates["content_json"] = content_json
        if model is not None:
            updates["model"] = model
        if prompt_tokens is not None:
            updates["prompt_tokens"] = prompt_tokens
        if completion_tokens is not None:
            updates["completion_tokens"] = completion_tokens
        if total_tokens is not None:
            updates["total_tokens"] = total_tokens
        if error_code is not None:
            updates["error_code"] = error_code

        with self._session() as session:
            result = session.execute(
                update(ChatbotMessage)
                .where(
                    ChatbotMessage.id == message_id,
                    ChatbotMessage.user_id == user_id,
                    ChatbotMessage.status == expected_status,
                )
                .values(**updates)
            )
            if result.rowcount == 0:
                return None
            model = session.scalar(select(ChatbotMessage).where(ChatbotMessage.id == message_id, ChatbotMessage.user_id == user_id))
            return self._record_from_model(model) if model is not None else None
