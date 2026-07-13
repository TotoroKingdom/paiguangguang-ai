from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from sqlalchemy import and_, desc, or_, select
from sqlalchemy.orm import Session

from app.chatbot.errors import ChatbotApiError
from app.chatbot.models.conversation import ChatbotConversation
from app.chatbot.models.llm_run import ChatbotLLMRun
from app.chatbot.repositories.cursor import (
    ConversationCursor,
    ConversationCursorError,
    decode_conversation_cursor,
    encode_conversation_cursor,
)
from app.chatbot.schemas.common import ConversationActiveGenerationData, DeleteResultData
from app.chatbot.schemas.conversation import (
    ConversationCreateRequest,
    ConversationData,
    ConversationDetailData,
    ConversationPageData,
    ConversationUpdateRequest,
)
from app.core.config import Settings, get_settings
from app.core.rate_limit import RateLimitConfig, get_rate_limiter


ConversationListStatus = Literal["active", "archived"]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ConversationService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def _allowed_models(self) -> set[str]:
        allowed = {model.strip() for model in self.settings.chatbot_allowed_models if model.strip()}
        if not allowed:
            allowed = {self.settings.chatbot_default_model}
        return allowed

    def _validate_model(self, model: str | None) -> str:
        candidate = (model or self.settings.chatbot_default_model).strip()
        if not candidate:
            raise ChatbotApiError(
                status_code=422,
                code="VALIDATION_ERROR",
                message="Model cannot be empty",
            )
        if candidate not in self._allowed_models():
            raise ChatbotApiError(
                status_code=422,
                code="CHATBOT_MODEL_NOT_ALLOWED",
                message="Model is not allowed",
                details={"model": candidate},
            )
        return candidate

    def _apply_rate_limit(self, user_id: str, *, conversation_id: str | None = None, operation: str) -> None:
        config = RateLimitConfig(
            max_requests=self.settings.chatbot_rate_limit_max_requests,
            window_seconds=self.settings.chatbot_rate_limit_window_seconds,
        )
        limiter = get_rate_limiter()
        limiter.check(f"chatbot:rate:user={user_id}", config, operation=operation)
        if conversation_id is not None:
            limiter.check(
                f"chatbot:rate:user={user_id}:conversation={conversation_id}",
                config,
                operation=operation,
            )

    @staticmethod
    def _normalize_title(title: str | None, *, default_title: str = "新对话") -> tuple[str, str]:
        if title is None:
            return default_title, "default"
        normalized = title.strip()
        if not normalized:
            raise ChatbotApiError(
                status_code=422,
                code="VALIDATION_ERROR",
                message="Title cannot be empty",
            )
        return normalized, "manual"

    @staticmethod
    def _conversation_data(model: ChatbotConversation) -> ConversationData:
        return ConversationData(
            id=model.id,
            title=model.title,
            title_source=model.title_source,
            status=model.status,
            model=model.model,
            last_message_at=model.last_message_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
            archived_at=model.archived_at,
        )

    @staticmethod
    def _detail_data(
        model: ChatbotConversation,
        active_generation: ConversationActiveGenerationData | None,
    ) -> ConversationDetailData:
        return ConversationDetailData(
            id=model.id,
            title=model.title,
            title_source=model.title_source,
            status=model.status,
            model=model.model,
            last_message_at=model.last_message_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
            archived_at=model.archived_at,
            active_generation=active_generation,
        )

    @staticmethod
    def _older_than_cursor_clause(cursor: ConversationCursor):
        return or_(
            ChatbotConversation.last_message_at < cursor.last_message_at,
            and_(
                ChatbotConversation.last_message_at == cursor.last_message_at,
                ChatbotConversation.id < cursor.conversation_id,
            ),
        )

    @staticmethod
    def _owned_statement(
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

    def _get_owned_conversation(
        self,
        session: Session,
        conversation_id: str,
        user_id: str,
        *,
        include_deleted: bool = False,
        for_update: bool = False,
    ) -> ChatbotConversation | None:
        stmt = self._owned_statement(
            conversation_id,
            user_id,
            include_deleted=include_deleted,
            for_update=for_update,
        )
        return session.scalar(stmt)

    def _get_active_generation(
        self,
        session: Session,
        *,
        conversation_id: str,
        user_id: str,
    ) -> ConversationActiveGenerationData | None:
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
        if model is None:
            return None
        return ConversationActiveGenerationData(
            assistant_message_id=model.message_id,
            status=model.status,
            started_at=model.started_at,
        )

    def create_conversation(
        self,
        session: Session,
        user_id: str,
        request: ConversationCreateRequest,
    ) -> ConversationData:
        self._apply_rate_limit(user_id, operation="Chatbot conversation creation")
        title, title_source = self._normalize_title(request.title)
        model = self._validate_model(request.model)
        now = _utcnow()
        row = ChatbotConversation(
            user_id=user_id,
            title=title,
            title_source=title_source,
            status="active",
            model=model,
            system_prompt_version="v1",
            next_sequence=1,
            last_message_at=now,
            archived_at=None,
            deleted_at=None,
            cleanup_status="pending",
            created_at=now,
            updated_at=now,
        )
        try:
            session.add(row)
            session.flush()
            session.refresh(row)
            session.commit()
        except Exception:
            session.rollback()
            raise
        return self._conversation_data(row)

    def list_conversations(
        self,
        session: Session,
        user_id: str,
        *,
        status: ConversationListStatus = "active",
        limit: int = 20,
        cursor: str | None = None,
    ) -> ConversationPageData:
        if limit < 1 or limit > 100:
            raise ChatbotApiError(
                status_code=422,
                code="VALIDATION_ERROR",
                message="limit must be between 1 and 100",
            )

        position: ConversationCursor | None = None
        if cursor is not None:
            try:
                position = decode_conversation_cursor(cursor, expected_status_filter=status)
            except ConversationCursorError as exc:
                raise ChatbotApiError(
                    status_code=400,
                    code="CHATBOT_INVALID_CURSOR",
                    message="Invalid conversation cursor",
                ) from exc

        stmt = select(ChatbotConversation).where(
            ChatbotConversation.user_id == user_id,
            ChatbotConversation.deleted_at.is_(None),
        )
        if status == "archived":
            stmt = stmt.where(ChatbotConversation.status == "archived")
        else:
            stmt = stmt.where(ChatbotConversation.status == "active")

        if position is not None:
            stmt = stmt.where(self._older_than_cursor_clause(position))

        stmt = stmt.order_by(desc(ChatbotConversation.last_message_at), desc(ChatbotConversation.id)).limit(limit + 1)
        rows = list(session.scalars(stmt))

        has_more = len(rows) > limit
        visible_rows = rows[:limit]
        items = [self._conversation_data(row) for row in visible_rows]
        next_cursor = None
        if has_more and visible_rows:
            tail = visible_rows[-1]
            next_cursor = encode_conversation_cursor(
                ConversationCursor(
                    last_message_at=tail.last_message_at,
                    conversation_id=tail.id,
                    status_filter=status,
                )
            )
        return ConversationPageData(items=items, next_cursor=next_cursor, has_more=has_more)

    def get_conversation(
        self,
        session: Session,
        user_id: str,
        conversation_id: str,
    ) -> ConversationDetailData:
        model = self._get_owned_conversation(session, conversation_id, user_id)
        if model is None:
            raise ChatbotApiError(
                status_code=404,
                code="CHATBOT_CONVERSATION_NOT_FOUND",
                message="Conversation not found",
            )
        active_generation = self._get_active_generation(session, conversation_id=conversation_id, user_id=user_id)
        return self._detail_data(model, active_generation)

    def update_conversation(
        self,
        session: Session,
        user_id: str,
        conversation_id: str,
        request: ConversationUpdateRequest,
    ) -> ConversationData:
        self._apply_rate_limit(
            user_id,
            conversation_id=conversation_id,
            operation="Chatbot conversation update",
        )
        model = self._get_owned_conversation(session, conversation_id, user_id, for_update=True)
        if model is None:
            raise ChatbotApiError(
                status_code=404,
                code="CHATBOT_CONVERSATION_NOT_FOUND",
                message="Conversation not found",
            )

        if request.title is not None:
            title, title_source = self._normalize_title(request.title)
            model.title = title
            model.title_source = title_source
        if request.model is not None:
            model.model = self._validate_model(request.model)
        model.updated_at = _utcnow()
        try:
            session.flush()
            session.commit()
        except Exception:
            session.rollback()
            raise
        return self._conversation_data(model)

    def archive_conversation(self, session: Session, user_id: str, conversation_id: str) -> ConversationData:
        self._apply_rate_limit(
            user_id,
            conversation_id=conversation_id,
            operation="Chatbot conversation archive",
        )
        model = self._get_owned_conversation(session, conversation_id, user_id, for_update=True)
        if model is None:
            raise ChatbotApiError(
                status_code=404,
                code="CHATBOT_CONVERSATION_NOT_FOUND",
                message="Conversation not found",
            )
        if model.status == "archived":
            return self._conversation_data(model)
        if model.status == "deleted":
            raise ChatbotApiError(
                status_code=404,
                code="CHATBOT_CONVERSATION_NOT_FOUND",
                message="Conversation not found",
            )
        active_generation = self._get_active_generation(session, conversation_id=conversation_id, user_id=user_id)
        if active_generation is not None:
            raise ChatbotApiError(
                status_code=409,
                code="CHATBOT_CONVERSATION_BUSY",
                message="Conversation is busy",
            )
        model.status = "archived"
        model.archived_at = _utcnow()
        model.updated_at = _utcnow()
        try:
            session.flush()
            session.commit()
        except Exception:
            session.rollback()
            raise
        return self._conversation_data(model)

    def restore_conversation(self, session: Session, user_id: str, conversation_id: str) -> ConversationData:
        self._apply_rate_limit(
            user_id,
            conversation_id=conversation_id,
            operation="Chatbot conversation restore",
        )
        model = self._get_owned_conversation(session, conversation_id, user_id, for_update=True)
        if model is None or model.status == "deleted":
            raise ChatbotApiError(
                status_code=404,
                code="CHATBOT_CONVERSATION_NOT_FOUND",
                message="Conversation not found",
            )
        if model.status == "active":
            return self._conversation_data(model)
        model.status = "active"
        model.archived_at = None
        model.updated_at = _utcnow()
        try:
            session.flush()
            session.commit()
        except Exception:
            session.rollback()
            raise
        return self._conversation_data(model)

    def delete_conversation(self, session: Session, user_id: str, conversation_id: str) -> DeleteResultData:
        self._apply_rate_limit(
            user_id,
            conversation_id=conversation_id,
            operation="Chatbot conversation delete",
        )
        model = self._get_owned_conversation(session, conversation_id, user_id, for_update=True)
        if model is None or model.status == "deleted":
            raise ChatbotApiError(
                status_code=404,
                code="CHATBOT_CONVERSATION_NOT_FOUND",
                message="Conversation not found",
            )
        model.status = "deleted"
        model.deleted_at = _utcnow()
        model.cleanup_status = "pending"
        model.updated_at = _utcnow()
        try:
            session.flush()
            session.commit()
        except Exception:
            session.rollback()
            raise
        return DeleteResultData(id=model.id, status="deleted", cleanup_status=model.cleanup_status)


_CONVERSATION_SERVICE: ConversationService | None = None


def get_conversation_service() -> ConversationService:
    global _CONVERSATION_SERVICE
    if _CONVERSATION_SERVICE is None:
        _CONVERSATION_SERVICE = ConversationService()
    return _CONVERSATION_SERVICE
