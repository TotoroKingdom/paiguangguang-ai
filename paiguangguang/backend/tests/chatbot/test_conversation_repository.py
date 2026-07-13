from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.models.conversation import ChatbotConversation
from app.chatbot.repositories.conversation_repository import ConversationRepository
from app.chatbot.repositories.cursor import (
    ConversationCursor,
    ConversationCursorError,
    decode_conversation_cursor,
    encode_conversation_cursor,
)
from app.db.models import Base, User


def _build_session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_engine(f"sqlite+pysqlite:///{(tmp_path / f'{uuid4()}.sqlite3').as_posix()}", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def _create_user(session: Session, *, email: str, display_name: str = "Chatbot User") -> User:
    user = User(
        email=email,
        display_name=display_name,
        hashed_password="hashed-password",
    )
    session.add(user)
    session.flush()
    return user


def test_conversation_cursor_round_trip_and_validation() -> None:
    cursor = ConversationCursor(
        last_message_at=datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc),
        conversation_id="00000000-0000-0000-0000-000000000123",
        status_filter="active",
    )

    encoded = encode_conversation_cursor(cursor)
    decoded = decode_conversation_cursor(encoded, expected_status_filter="active")

    assert decoded == cursor


def test_conversation_cursor_rejects_invalid_payloads() -> None:
    cursor = ConversationCursor(
        last_message_at=datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc),
        conversation_id="00000000-0000-0000-0000-000000000123",
        status_filter="active",
    )
    encoded = encode_conversation_cursor(cursor)

    for token, expected_message in [
        ("not-a-cursor", "Invalid conversation cursor"),
        (encoded, "Conversation cursor filter mismatch"),
    ]:
        try:
            decode_conversation_cursor(token, expected_status_filter="archived")
        except ConversationCursorError as exc:
            assert expected_message in str(exc)
        else:  # pragma: no cover - defensive
            raise AssertionError("Expected cursor decode to fail")


def test_create_get_and_allocate_sequences_persist_defaults(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    repo = ConversationRepository(session_factory)

    with session_factory() as session:
        user = _create_user(session, email="owner@example.com")
        session.commit()

    created = repo.create(user.id, "  Draft title  ", "deepseek-chat")

    assert created.user_id == user.id
    assert created.title == "  Draft title  "
    assert created.title_source == "default"
    assert created.status == "active"
    assert created.model == "deepseek-chat"
    assert created.system_prompt_version == "v1"
    assert created.next_sequence == 1
    assert created.cleanup_status == "pending"
    assert created.deleted_at is None

    with session_factory() as session:
        row = session.get(ChatbotConversation, created.id)
        assert row is not None
        allocated = repo.allocate_sequences(row.id, 3)
        session.refresh(row)

    assert allocated == [1, 2, 3]
    assert row.next_sequence == 4

    found = repo.get_owned(created.id, user.id)
    assert found is not None
    assert found.id == created.id
    assert repo.get_owned(created.id, "00000000-0000-0000-0000-000000000999") is None


def test_get_owned_hides_deleted_by_default(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    repo = ConversationRepository(session_factory)

    with session_factory() as session:
        user = _create_user(session, email="owner@example.com")
        session.commit()
        created = repo.create(user.id, "Active", "deepseek-chat")
        row = session.get(ChatbotConversation, created.id)
        assert row is not None
        row.status = "deleted"
        row.deleted_at = datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc)
        session.commit()

    assert repo.get_owned(created.id, user.id) is None
    assert repo.get_owned(created.id, user.id, include_deleted=True) is not None


def test_list_owned_filters_by_owner_status_and_stable_cursor(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    repo = ConversationRepository(session_factory)

    with session_factory() as session:
        owner = _create_user(session, email="owner@example.com")
        other = _create_user(session, email="other@example.com")
        session.add_all(
            [
                ChatbotConversation(
                    id="00000000-0000-0000-0000-000000000003",
                    user_id=owner.id,
                    title="Archived",
                    title_source="default",
                    status="archived",
                    model="deepseek-chat",
                    system_prompt_version="v1",
                    next_sequence=1,
                    last_message_at=datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc),
                    cleanup_status="pending",
                    created_at=datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc),
                    updated_at=datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc),
                ),
                ChatbotConversation(
                    id="00000000-0000-0000-0000-000000000002",
                    user_id=owner.id,
                    title="Active A",
                    title_source="default",
                    status="active",
                    model="deepseek-chat",
                    system_prompt_version="v1",
                    next_sequence=1,
                    last_message_at=datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc),
                    cleanup_status="pending",
                    created_at=datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc),
                    updated_at=datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc),
                ),
                ChatbotConversation(
                    id="00000000-0000-0000-0000-000000000001",
                    user_id=owner.id,
                    title="Active B",
                    title_source="default",
                    status="active",
                    model="deepseek-chat",
                    system_prompt_version="v1",
                    next_sequence=1,
                    last_message_at=datetime(2026, 7, 13, 11, 59, tzinfo=timezone.utc),
                    cleanup_status="pending",
                    created_at=datetime(2026, 7, 13, 11, 59, tzinfo=timezone.utc),
                    updated_at=datetime(2026, 7, 13, 11, 59, tzinfo=timezone.utc),
                ),
                ChatbotConversation(
                    id="00000000-0000-0000-0000-000000000099",
                    user_id=other.id,
                    title="Foreign",
                    title_source="default",
                    status="active",
                    model="deepseek-chat",
                    system_prompt_version="v1",
                    next_sequence=1,
                    last_message_at=datetime(2026, 7, 13, 12, 1, tzinfo=timezone.utc),
                    cleanup_status="pending",
                    created_at=datetime(2026, 7, 13, 12, 1, tzinfo=timezone.utc),
                    updated_at=datetime(2026, 7, 13, 12, 1, tzinfo=timezone.utc),
                ),
            ]
        )
        session.commit()

    first_page = repo.list_owned(owner.id, "active", None, 2)
    assert [item.id for item in first_page.items] == [
        "00000000-0000-0000-0000-000000000002",
        "00000000-0000-0000-0000-000000000001",
    ]
    assert first_page.has_more is False
    assert first_page.next_cursor is None

    archived_page = repo.list_owned(owner.id, "archived", None, 10)
    assert [item.id for item in archived_page.items] == ["00000000-0000-0000-0000-000000000003"]

    all_active_with_deleted = repo.list_owned(owner.id, None, None, 10)
    assert [item.id for item in all_active_with_deleted.items] == [
        "00000000-0000-0000-0000-000000000003",
        "00000000-0000-0000-0000-000000000002",
        "00000000-0000-0000-0000-000000000001",
    ]


def test_list_owned_uses_cursor_for_older_pages(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    repo = ConversationRepository(session_factory)

    with session_factory() as session:
        user = _create_user(session, email="owner@example.com")
        session.add_all(
            [
                ChatbotConversation(
                    id="00000000-0000-0000-0000-000000000004",
                    user_id=user.id,
                    title="Newest",
                    title_source="default",
                    status="active",
                    model="deepseek-chat",
                    system_prompt_version="v1",
                    next_sequence=1,
                    last_message_at=datetime(2026, 7, 13, 12, 3, tzinfo=timezone.utc),
                    cleanup_status="pending",
                    created_at=datetime(2026, 7, 13, 12, 3, tzinfo=timezone.utc),
                    updated_at=datetime(2026, 7, 13, 12, 3, tzinfo=timezone.utc),
                ),
                ChatbotConversation(
                    id="00000000-0000-0000-0000-000000000003",
                    user_id=user.id,
                    title="Middle",
                    title_source="default",
                    status="active",
                    model="deepseek-chat",
                    system_prompt_version="v1",
                    next_sequence=1,
                    last_message_at=datetime(2026, 7, 13, 12, 2, tzinfo=timezone.utc),
                    cleanup_status="pending",
                    created_at=datetime(2026, 7, 13, 12, 2, tzinfo=timezone.utc),
                    updated_at=datetime(2026, 7, 13, 12, 2, tzinfo=timezone.utc),
                ),
                ChatbotConversation(
                    id="00000000-0000-0000-0000-000000000002",
                    user_id=user.id,
                    title="Oldest",
                    title_source="default",
                    status="active",
                    model="deepseek-chat",
                    system_prompt_version="v1",
                    next_sequence=1,
                    last_message_at=datetime(2026, 7, 13, 12, 1, tzinfo=timezone.utc),
                    cleanup_status="pending",
                    created_at=datetime(2026, 7, 13, 12, 1, tzinfo=timezone.utc),
                    updated_at=datetime(2026, 7, 13, 12, 1, tzinfo=timezone.utc),
                ),
            ]
        )
        session.commit()

    page_one = repo.list_owned(user.id, "active", None, 2)
    assert [item.id for item in page_one.items] == [
        "00000000-0000-0000-0000-000000000004",
        "00000000-0000-0000-0000-000000000003",
    ]
    assert page_one.has_more is True
    assert page_one.next_cursor is not None

    cursor = decode_conversation_cursor(page_one.next_cursor, expected_status_filter="active")
    page_two = repo.list_owned(user.id, "active", cursor, 2)
    assert [item.id for item in page_two.items] == ["00000000-0000-0000-0000-000000000002"]
    assert page_two.has_more is False


def test_lock_owned_uses_for_update_and_respects_owner(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    repo = ConversationRepository(session_factory)

    with session_factory() as session:
        owner = _create_user(session, email="owner@example.com")
        foreign = _create_user(session, email="other@example.com")
        conversation = ChatbotConversation(
            id="00000000-0000-0000-0000-000000000777",
            user_id=owner.id,
            title="Lock me",
            title_source="default",
            status="active",
            model="deepseek-chat",
            system_prompt_version="v1",
            next_sequence=1,
            last_message_at=datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc),
            cleanup_status="pending",
            created_at=datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc),
        )
        session.add(conversation)
        session.commit()

    locked = repo.lock_owned("00000000-0000-0000-0000-000000000777", owner.id)
    foreign_locked = repo.lock_owned("00000000-0000-0000-0000-000000000777", foreign.id)
    statement = repo._build_owned_statement(
        "00000000-0000-0000-0000-000000000777",
        owner.id,
        for_update=True,
    )

    assert locked is not None
    assert foreign_locked is None
    assert statement._for_update_arg is not None
