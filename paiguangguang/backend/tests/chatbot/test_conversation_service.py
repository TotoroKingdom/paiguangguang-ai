from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.models.llm_run import ChatbotLLMRun
from app.chatbot.models.message import ChatbotMessage
from app.chatbot.schemas.conversation import ConversationCreateRequest, ConversationUpdateRequest
from app.chatbot.services.conversation_service import ChatbotApiError, ConversationService
from app.core.config import Settings
from app.db.models import Base, User


def _build_session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_engine(f"sqlite+pysqlite:///{(tmp_path / f'{uuid4()}.sqlite3').as_posix()}", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def _create_user(session: Session, *, email: str) -> User:
    user = User(email=email, display_name="Chatbot User", hashed_password="hashed-password")
    session.add(user)
    session.flush()
    return user


def _make_service() -> ConversationService:
    return ConversationService(
        settings=Settings(
            chatbot_default_model="deepseek-chat",
            chatbot_allowed_models=["deepseek-chat"],
            chatbot_conversation_page_size=20,
        )
    )


def test_conversation_service_state_machine_cursor_and_generation(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    service = _make_service()

    with session_factory() as session:
        owner = _create_user(session, email="owner@example.com")
        session.commit()

        default_conv = service.create_conversation(session, owner.id, ConversationCreateRequest())
        manual_conv = service.create_conversation(
            session,
            owner.id,
            ConversationCreateRequest(title="  生产级 Chatbot 设计  "),
        )

        assert default_conv.title == "新对话"
        assert default_conv.title_source == "default"
        assert default_conv.model == "deepseek-chat"
        assert manual_conv.title == "生产级 Chatbot 设计"
        assert manual_conv.title_source == "manual"

        page = service.list_conversations(session, owner.id, status="active", limit=1, cursor=None)
        assert [item.id for item in page.items] == [manual_conv.id]
        assert page.has_more is True
        assert page.next_cursor is not None

        next_page = service.list_conversations(session, owner.id, status="active", limit=1, cursor=page.next_cursor)
        assert [item.id for item in next_page.items] == [default_conv.id]
        assert next_page.has_more is False

        with pytest.raises(ChatbotApiError) as exc:
            service.list_conversations(session, owner.id, status="active", limit=1, cursor="not-a-cursor")
        assert exc.value.code == "CHATBOT_INVALID_CURSOR"

        user_message = ChatbotMessage(
            id="00000000-0000-0000-0000-000000010001",
            conversation_id=str(default_conv.id),
            user_id=owner.id,
            role="user",
            content="请总结当前架构选择",
            sequence_number=1,
            status="completed",
            client_request_id="00000000-0000-0000-0000-000000010000",
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            created_at=datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc),
        )
        active_run = ChatbotLLMRun(
            id="00000000-0000-0000-0000-000000010002",
            request_id="00000000-0000-0000-0000-000000010003",
            user_id=owner.id,
            conversation_id=str(default_conv.id),
            message_id=user_message.id,
            provider="deepseek",
            model="deepseek-chat",
            prompt_version="v1",
            status="streaming",
            attempt_count=1,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            started_at=datetime(2026, 7, 13, 12, 1, tzinfo=timezone.utc),
            created_at=datetime(2026, 7, 13, 12, 1, tzinfo=timezone.utc),
            updated_at=datetime(2026, 7, 13, 12, 1, tzinfo=timezone.utc),
        )
        session.add_all([user_message, active_run])
        session.commit()

        default_conv_id = str(default_conv.id)
        manual_conv_id = str(manual_conv.id)

        detail = service.get_conversation(session, owner.id, default_conv_id)
        assert detail.active_generation is not None
        assert detail.active_generation.assistant_message_id == user_message.id
        assert detail.active_generation.status == "streaming"

        updated = service.update_conversation(
            session,
            owner.id,
            default_conv_id,
            ConversationUpdateRequest(title="  新标题  ", model="deepseek-chat"),
        )
        assert updated.title == "新标题"
        assert updated.title_source == "manual"

        with pytest.raises(ChatbotApiError) as exc_busy:
            service.archive_conversation(session, owner.id, default_conv_id)
        assert exc_busy.value.code == "CHATBOT_CONVERSATION_BUSY"

        archived = service.archive_conversation(session, owner.id, manual_conv_id)
        assert archived.status == "archived"
        archived_again = service.archive_conversation(session, owner.id, manual_conv_id)
        assert archived_again.status == "archived"

        restored = service.restore_conversation(session, owner.id, manual_conv_id)
        assert restored.status == "active"
        restored_again = service.restore_conversation(session, owner.id, manual_conv_id)
        assert restored_again.status == "active"

        deleted = service.delete_conversation(session, owner.id, manual_conv_id)
        assert deleted.status == "deleted"
        assert deleted.cleanup_status == "pending"

        with pytest.raises(ChatbotApiError) as exc_missing:
            service.get_conversation(session, owner.id, manual_conv_id)
        assert exc_missing.value.code == "CHATBOT_CONVERSATION_NOT_FOUND"


def test_conversation_service_rejects_bad_model_and_foreign_access(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    service = _make_service()

    with session_factory() as session:
        owner = _create_user(session, email="owner@example.com")
        foreign = _create_user(session, email="foreign@example.com")
        session.commit()

        with pytest.raises(ChatbotApiError) as exc:
            service.create_conversation(
                session,
                owner.id,
                ConversationCreateRequest(title="Hello", model="gpt-4"),
            )
        assert exc.value.code == "CHATBOT_MODEL_NOT_ALLOWED"

        conversation = service.create_conversation(
            session,
            owner.id,
            ConversationCreateRequest(title="Hello", model="deepseek-chat"),
        )
        conversation_id = str(conversation.id)

        with pytest.raises(ChatbotApiError) as exc_foreign:
            service.get_conversation(session, foreign.id, conversation_id)
        assert exc_foreign.value.code == "CHATBOT_CONVERSATION_NOT_FOUND"

        with pytest.raises(ValidationError):
            ConversationUpdateRequest()
