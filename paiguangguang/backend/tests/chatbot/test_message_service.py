from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.repositories.conversation_repository import ConversationRepository
from app.chatbot.repositories.message_repository import MessageRepository, MessageCursor
from app.chatbot.services.conversation_service import ConversationService
from app.chatbot.services.message_service import ChatbotApiError, MessageService
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


def _build_service(session_factory: sessionmaker[Session]) -> MessageService:
    return MessageService(
        conversation_repository=ConversationRepository(session_factory),
        message_repository=MessageRepository(session_factory),
    )


def _build_conversation_service() -> ConversationService:
    return ConversationService()


def _seed_messages(
    session_factory: sessionmaker[Session],
    *,
    owner_email: str = "owner@example.com",
    turn_count: int = 2,
) -> tuple[str, str, MessageRepository]:
    conversation_repo = ConversationRepository(session_factory)
    message_repo = MessageRepository(session_factory)
    with session_factory() as session:
        owner = _create_user(session, email=owner_email)
        session.commit()
    conversation_id = conversation_repo.create(owner.id, "Thread", "deepseek-chat").id
    for index in range(turn_count):
        user_message, assistant_message = message_repo.create_user_and_assistant(
            conversation_id,
            owner.id,
            content=f"message-{index}",
            client_request_id=f"00000000-0000-0000-0000-00000000{index:04d}",
            assistant_model="deepseek-chat",
        )
        if index == 0:
            message_repo.checkpoint(
                assistant_message.id,
                owner.id,
                expected_status="pending",
                content="partial",
            )
            message_repo.finalize(
                assistant_message.id,
                owner.id,
                expected_status="streaming",
                status="failed",
                content="partial",
                error_code="CHATBOT_LLM_TIMEOUT",
            )
    return conversation_id, owner.id, message_repo


def test_message_service_lists_latest_page_and_preserves_partial_failed_content(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    service = _build_service(session_factory)
    conversation_id, owner_id, _ = _seed_messages(session_factory, turn_count=3)

    with session_factory() as session:
        page = service.list_messages(session, owner_id, conversation_id, limit=50, before=None)

    assert [item.sequence_number for item in page.items] == [1, 2, 3, 4, 5, 6]
    assert page.has_more is False
    assert page.next_cursor is None
    assert page.items[1].status == "failed"
    assert page.items[1].content == "partial"
    assert page.items[1].error_code == "CHATBOT_LLM_TIMEOUT"
    assert all(not hasattr(item, "user_id") for item in page.items)


def test_message_service_paginates_ascending_and_is_cursor_stable(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    service = _build_service(session_factory)
    conversation_id, owner_id, message_repo = _seed_messages(session_factory, turn_count=60)

    with session_factory() as session:
        first_page = service.list_messages(session, owner_id, conversation_id, limit=50, before=None)

    assert [item.sequence_number for item in first_page.items] == list(range(71, 121))
    assert first_page.has_more is True
    assert first_page.next_cursor is not None

    original_cursor = first_page.next_cursor
    with session_factory() as session:
        before_cursor = MessageCursor(conversation_id=conversation_id, before_sequence_number=71)
        second_page = service.list_messages(session, owner_id, conversation_id, limit=50, before=before_cursor)

    assert [item.sequence_number for item in second_page.items] == list(range(21, 71))

    message_repo.create_user_and_assistant(
        conversation_id,
        owner_id,
        content="newer turn",
        client_request_id="00000000-0000-0000-0000-000000009999",
        assistant_model="deepseek-chat",
    )

    with session_factory() as session:
        page_after_insert = service.list_messages(session, owner_id, conversation_id, limit=50, before=MessageCursor(conversation_id=conversation_id, before_sequence_number=71))

    assert [item.sequence_number for item in page_after_insert.items] == list(range(21, 71))

    with session_factory() as session:
        first_cursor_page = service.list_messages(session, owner_id, conversation_id, limit=50, before=MessageCursor(conversation_id=conversation_id, before_sequence_number=121))
    assert first_cursor_page.next_cursor == original_cursor


def test_message_service_rejects_deleted_conversation_and_invalid_cursor(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    service = _build_service(session_factory)
    conversation_repo = ConversationRepository(session_factory)
    message_repo = MessageRepository(session_factory)

    with session_factory() as session:
        owner = _create_user(session, email="owner@example.com")
        _create_user(session, email="foreign@example.com")
        session.commit()

    conversation = conversation_repo.create(owner.id, "Thread", "deepseek-chat")
    message_repo.create_user_and_assistant(
        conversation.id,
        owner.id,
        content="hello",
        client_request_id="00000000-0000-0000-0000-000000001111",
        assistant_model="deepseek-chat",
    )
    with session_factory() as session:
        with pytest.raises(ChatbotApiError) as exc_invalid:
            service.list_messages(session, owner.id, conversation.id, limit=50, before="not-a-cursor")
        assert exc_invalid.value.code == "CHATBOT_INVALID_CURSOR"

    with session_factory() as session:
        _build_conversation_service().delete_conversation(session, owner.id, conversation.id)

    with session_factory() as session:
        with pytest.raises(ChatbotApiError) as exc:
            service.list_messages(session, owner.id, conversation.id, limit=50, before=None)
        assert exc.value.code == "CHATBOT_CONVERSATION_NOT_FOUND"
