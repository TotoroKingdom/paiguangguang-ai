from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.chatbot.errors import ChatbotApiError
from app.chatbot.models.conversation import ChatbotConversation
from app.chatbot.models.message import ChatbotMessage
from app.chatbot.repositories.message_repository import (
    MessageCursor,
    MessageCursorError,
    decode_message_cursor,
    encode_message_cursor,
)
from app.chatbot.schemas.message import MessageData, MessagePageData


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


MessageCursorLike = MessageCursor | str | None
MessageListStatus = Literal["active", "archived"]


class MessageService:
    def __init__(self, conversation_repository=None, message_repository=None) -> None:
        self.conversation_repository = conversation_repository
        self.message_repository = message_repository

    @staticmethod
    def _message_data(model: ChatbotMessage) -> MessageData:
        return MessageData(
            id=model.id,
            conversation_id=model.conversation_id,
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
    def _owned_conversation_statement(conversation_id: str, user_id: str):
        return select(ChatbotConversation).where(
            ChatbotConversation.id == conversation_id,
            ChatbotConversation.user_id == user_id,
            ChatbotConversation.deleted_at.is_(None),
        )

    @staticmethod
    def _message_statement(
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

    def list_messages(
        self,
        session: Session,
        user_id: str,
        conversation_id: str,
        *,
        limit: int = 50,
        before: MessageCursorLike = None,
        status: MessageListStatus = "active",
    ) -> MessagePageData:
        if limit < 1 or limit > 100:
            raise ChatbotApiError(
                status_code=422,
                code="VALIDATION_ERROR",
                message="limit must be between 1 and 100",
            )
        if status not in {"active", "archived"}:
            raise ChatbotApiError(
                status_code=422,
                code="VALIDATION_ERROR",
                message="Invalid conversation status",
            )

        conversation = session.scalar(self._owned_conversation_statement(conversation_id, user_id))
        if conversation is None or (status == "active" and conversation.status != "active" and conversation.status != "archived"):
            raise ChatbotApiError(
                status_code=404,
                code="CHATBOT_CONVERSATION_NOT_FOUND",
                message="Conversation not found",
            )

        before_cursor: MessageCursor | None = None
        if isinstance(before, str):
            try:
                before_cursor = decode_message_cursor(before, expected_conversation_id=conversation_id)
            except MessageCursorError as exc:
                raise ChatbotApiError(
                    status_code=400,
                    code="CHATBOT_INVALID_CURSOR",
                    message="Invalid message cursor",
                ) from exc
        elif isinstance(before, MessageCursor):
            if before.conversation_id != conversation_id:
                raise ChatbotApiError(
                    status_code=400,
                    code="CHATBOT_INVALID_CURSOR",
                    message="Message cursor conversation mismatch",
                )
            before_cursor = before

        stmt = self._message_statement(
            conversation_id,
            user_id,
            before_sequence_number=before_cursor.before_sequence_number if before_cursor is not None else None,
        )
        stmt = stmt.order_by(desc(ChatbotMessage.sequence_number), desc(ChatbotMessage.id)).limit(limit + 1)
        rows = list(session.scalars(stmt))

        has_more = len(rows) > limit
        visible_rows = rows[:limit]
        items = [self._message_data(row) for row in reversed(visible_rows)]
        next_cursor = None
        if has_more and visible_rows:
            next_cursor = encode_message_cursor(
                MessageCursor(
                    conversation_id=conversation_id,
                    before_sequence_number=visible_rows[-1].sequence_number,
                )
            )
        return MessagePageData(items=items, next_cursor=next_cursor, has_more=has_more)


_MESSAGE_SERVICE: MessageService | None = None


def get_message_service() -> MessageService:
    global _MESSAGE_SERVICE
    if _MESSAGE_SERVICE is None:
        _MESSAGE_SERVICE = MessageService()
    return _MESSAGE_SERVICE
