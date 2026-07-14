from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.models.conversation import ChatbotConversation
from app.chatbot.models.job import ChatbotJob
from app.chatbot.models.message import ChatbotMessage
from app.chatbot.repositories.job_repository import JobRepository
from app.chatbot.services.completion_jobs import CompletionJobService, ConversationTitleService
from app.core.config import Settings
from app.db.base import Base
from app.db.models import User


def _seed_completed_turn(
    tmp_path: Path,
    *,
    user_content: str = "hello",
) -> tuple[sessionmaker[Session], str, str, str, str]:
    engine = create_engine(
        f"sqlite+pysqlite:///{(tmp_path / f'{uuid4()}.sqlite3').as_posix()}",
        future=True,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    with factory() as session:
        owner = User(
            email=f"owner-{uuid4()}@example.com",
            display_name="Owner",
            hashed_password="hashed-password",
        )
        session.add(owner)
        session.flush()
        conversation = ChatbotConversation(
            user_id=owner.id,
            title="新对话",
            title_source="default",
            status="active",
            model="deepseek-chat",
            system_prompt_version="v1",
        )
        session.add(conversation)
        session.flush()
        user_message = ChatbotMessage(
            conversation_id=conversation.id,
            user_id=owner.id,
            role="user",
            content=user_content,
            sequence_number=1,
            status="completed",
            client_request_id=str(uuid4()),
        )
        session.add(user_message)
        session.flush()
        assistant_message = ChatbotMessage(
            conversation_id=conversation.id,
            user_id=owner.id,
            role="assistant",
            content="Project summary",
            sequence_number=2,
            status="completed",
            client_request_id=None,
            parent_message_id=user_message.id,
            model="deepseek-chat",
        )
        session.add(assistant_message)
        session.commit()
        return factory, owner.id, conversation.id, user_message.id, assistant_message.id


def test_completion_jobs_are_deduplicated(tmp_path) -> None:
    factory, owner_id, conversation_id, user_message_id, assistant_message_id = (
        _seed_completed_turn(tmp_path)
    )
    service = CompletionJobService(
        JobRepository(factory),
        settings=Settings(chatbot_long_term_memory_enabled=True),
    )
    with factory() as session:
        for _ in range(2):
            service.enqueue_completed_turn(
                session,
                user_id=owner_id,
                conversation_id=conversation_id,
                user_message_id=user_message_id,
                assistant_message_id=assistant_message_id,
            )
        session.commit()

    with factory() as session:
        jobs = list(session.scalars(select(ChatbotJob).order_by(ChatbotJob.kind)))
    assert {job.kind for job in jobs} == {
        "auto_title",
        "completed_turn_memory",
        "refresh_conversation_context",
    }
    assert len(jobs) == 3


def test_auto_title_uses_first_user_message(tmp_path) -> None:
    factory, owner_id, conversation_id, user_message_id, assistant_message_id = (
        _seed_completed_turn(
            tmp_path,
            user_content="  Design   a durable chatbot worker with retries  ",
        )
    )
    changed = ConversationTitleService(factory).apply_auto_title(
        {
            "user_id": owner_id,
            "conversation_id": conversation_id,
            "user_message_id": user_message_id,
            "assistant_message_id": assistant_message_id,
        }
    )
    assert changed is True
    with factory() as session:
        row = session.get(ChatbotConversation, conversation_id)
    assert row is not None
    assert row.title == "Design a durable chatbot worker with retries"
    assert row.title_source == "auto"


def test_auto_title_never_overwrites_manual_title(tmp_path) -> None:
    factory, owner_id, conversation_id, user_message_id, assistant_message_id = (
        _seed_completed_turn(tmp_path)
    )
    with factory() as session:
        row = session.get(ChatbotConversation, conversation_id)
        assert row is not None
        row.title = "My manual title"
        row.title_source = "manual"
        session.commit()

    changed = ConversationTitleService(factory).apply_auto_title(
        {
            "user_id": owner_id,
            "conversation_id": conversation_id,
            "user_message_id": user_message_id,
            "assistant_message_id": assistant_message_id,
        }
    )
    assert changed is False
    with factory() as session:
        row = session.get(ChatbotConversation, conversation_id)
    assert row is not None
    assert row.title == "My manual title"
    assert row.title_source == "manual"
