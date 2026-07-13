from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.models.conversation import ChatbotConversation
from app.chatbot.models.message import ChatbotMessage
from app.chatbot.repositories.conversation_repository import ConversationRepository
from app.chatbot.repositories.message_repository import (
    MessageCursor,
    MessageCursorError,
    MessageRepository,
    decode_message_cursor,
    encode_message_cursor,
)
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


def _create_conversation(repo: ConversationRepository, user_id: str, title: str) -> str:
    conversation = repo.create(user_id, title, "deepseek-chat")
    return conversation.id


def test_create_user_and_assistant_pair_and_lookup_by_client_request_id(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    conversation_repo = ConversationRepository(session_factory)
    repo = MessageRepository(session_factory)

    with session_factory() as session:
        user = _create_user(session, email="owner@example.com")
        session.commit()

    conversation_id = _create_conversation(conversation_repo, user.id, "Thread")

    pair = repo.create_user_and_assistant(
        conversation_id,
        user.id,
        content="请总结当前架构选择",
        client_request_id="33d02ac4-4727-46d7-99b1-24f59e020ad5",
        assistant_model="deepseek-chat",
    )

    user_message, assistant_message = pair
    assert user_message.sequence_number == 1
    assert user_message.status == "completed"
    assert user_message.client_request_id == "33d02ac4-4727-46d7-99b1-24f59e020ad5"
    assert assistant_message.sequence_number == 2
    assert assistant_message.parent_message_id == user_message.id
    assert assistant_message.status == "pending"
    assert assistant_message.model == "deepseek-chat"

    found = repo.get_by_client_request_id(conversation_id, user.id, "33d02ac4-4727-46d7-99b1-24f59e020ad5")
    assert found is not None
    assert found.id == user_message.id

    with session_factory() as session:
        conversation = session.get(ChatbotConversation, conversation_id)
        assert conversation is not None
        assert conversation.next_sequence == 3


def test_list_owned_messages_paginates_before_cursor_in_ascending_order(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    conversation_repo = ConversationRepository(session_factory)
    repo = MessageRepository(session_factory)

    with session_factory() as session:
        owner = _create_user(session, email="owner@example.com")
        session.commit()

    conversation_id = _create_conversation(conversation_repo, owner.id, "Thread")

    repo.create_user_and_assistant(
        conversation_id,
        owner.id,
        content="第一条",
        client_request_id="00000000-0000-0000-0000-000000000101",
        assistant_model="deepseek-chat",
    )
    repo.create_user_and_assistant(
        conversation_id,
        owner.id,
        content="第二条",
        client_request_id="00000000-0000-0000-0000-000000000102",
        assistant_model="deepseek-chat",
    )

    first_page = repo.list_owned(conversation_id, owner.id, None, 2)
    assert [item.sequence_number for item in first_page.items] == [3, 4]
    assert first_page.has_more is True
    assert first_page.next_cursor is not None

    cursor = decode_message_cursor(first_page.next_cursor, expected_conversation_id=conversation_id)
    assert cursor.before_sequence_number == 3

    second_page = repo.list_owned(conversation_id, owner.id, cursor, 2)
    assert [item.sequence_number for item in second_page.items] == [1, 2]
    assert second_page.has_more is False
    assert second_page.next_cursor is None


def test_list_owned_and_lookup_are_owner_safe(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    conversation_repo = ConversationRepository(session_factory)
    repo = MessageRepository(session_factory)

    with session_factory() as session:
        owner = _create_user(session, email="owner@example.com")
        foreign = _create_user(session, email="foreign@example.com")
        session.commit()

    owner_conversation_id = _create_conversation(conversation_repo, owner.id, "Owner thread")
    foreign_conversation_id = _create_conversation(conversation_repo, foreign.id, "Foreign thread")

    repo.create_user_and_assistant(
        owner_conversation_id,
        owner.id,
        content="owner content",
        client_request_id="00000000-0000-0000-0000-000000000201",
        assistant_model="deepseek-chat",
    )
    repo.create_user_and_assistant(
        foreign_conversation_id,
        foreign.id,
        content="foreign content",
        client_request_id="00000000-0000-0000-0000-000000000202",
        assistant_model="deepseek-chat",
    )

    assert repo.list_owned(owner_conversation_id, foreign.id, None, 10).items == []
    assert repo.get_by_client_request_id(owner_conversation_id, foreign.id, "00000000-0000-0000-0000-000000000201") is None


def test_checkpoint_and_finalize_use_compare_and_set(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    conversation_repo = ConversationRepository(session_factory)
    repo = MessageRepository(session_factory)

    with session_factory() as session:
        owner = _create_user(session, email="owner@example.com")
        session.commit()

    conversation_id = _create_conversation(conversation_repo, owner.id, "Thread")
    _, assistant_message = repo.create_user_and_assistant(
        conversation_id,
        owner.id,
        content="请回答",
        client_request_id="00000000-0000-0000-0000-000000000301",
        assistant_model="deepseek-chat",
    )

    checkpointed = repo.checkpoint(
        assistant_message.id,
        owner.id,
        expected_status="pending",
        content="部分内容",
        content_json={"chunks": [{"delta": "部分内容"}]},
    )
    assert checkpointed is not None
    assert checkpointed.status == "streaming"
    assert checkpointed.content == "部分内容"
    assert checkpointed.content_json == {"chunks": [{"delta": "部分内容"}]}

    assert (
        repo.checkpoint(
            assistant_message.id,
            owner.id,
            expected_status="pending",
            content="不应写入",
        )
        is None
    )

    finalized = repo.finalize(
        assistant_message.id,
        owner.id,
        expected_status="streaming",
        status="completed",
        content="最终内容",
        prompt_tokens=10,
        completion_tokens=20,
        total_tokens=30,
    )
    assert finalized is not None
    assert finalized.status == "completed"
    assert finalized.content == "最终内容"
    assert finalized.prompt_tokens == 10
    assert finalized.completion_tokens == 20
    assert finalized.total_tokens == 30

    assert (
        repo.finalize(
            assistant_message.id,
            owner.id,
            expected_status="streaming",
            status="failed",
            error_code="CHATBOT_LLM_TIMEOUT",
        )
        is None
    )


def test_message_cursor_round_trip_and_validation() -> None:
    cursor = MessageCursor(
        conversation_id="00000000-0000-0000-0000-000000000123",
        before_sequence_number=42,
    )

    encoded = encode_message_cursor(cursor)
    decoded = decode_message_cursor(encoded, expected_conversation_id="00000000-0000-0000-0000-000000000123")
    assert decoded == cursor

    try:
        decode_message_cursor("not-a-cursor", expected_conversation_id="00000000-0000-0000-0000-000000000123")
    except MessageCursorError as exc:
        assert "Invalid message cursor" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected cursor decode to fail")
