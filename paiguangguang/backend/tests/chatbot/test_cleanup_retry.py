from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.memory.short_term_memory import ShortTermMemoryService
from app.chatbot.models.conversation import ChatbotConversation
from app.chatbot.models.job import ChatbotJob
from app.chatbot.repositories.conversation_repository import ConversationRepository
from app.chatbot.repositories.job_repository import JobRepository
from app.chatbot.repositories.memory_repository import MemoryRepository
from app.chatbot.services.cleanup_service import CleanupService
from app.chatbot.services.conversation_service import ConversationService
from app.chatbot.services.job_runner import JobRunner
from app.core.config import Settings
from app.db.base import Base
from app.db.models import User


def _factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_engine(
        f"sqlite+pysqlite:///{(tmp_path / f'{uuid4()}.sqlite3').as_posix()}",
        future=True,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


class FakeSemanticIndex:
    enabled = True

    def __init__(self) -> None:
        self.fail_delete = True
        self.deleted: list[str] = []

    def delete_memory(self, memory_id: str) -> None:
        if self.fail_delete:
            raise RuntimeError("semantic index unavailable")
        self.deleted.append(memory_id)


def test_conversation_cleanup_retries_without_rolling_back_database_delete(tmp_path) -> None:
    factory = _factory(tmp_path)
    repository = JobRepository(factory)
    conversation_repository = ConversationRepository(factory)
    memory_repository = MemoryRepository(factory)
    settings = Settings(chatbot_job_max_attempts=3)
    conversation_service = ConversationService(settings, job_repository=repository)

    with factory() as session:
        owner = User(
            email="cleanup-owner@example.com",
            display_name="Cleanup Owner",
            hashed_password="hashed-password",
        )
        session.add(owner)
        session.commit()
    conversation = conversation_repository.create(
        owner.id, "Thread", "deepseek-chat", system_prompt_version="v1"
    )
    memory = memory_repository.create(
        owner.id,
        memory_type="project_context",
        content="remember this",
        normalized_hash="cleanup-memory-hash",
        conversation_id=conversation.id,
        status="active",
        embedding_status="indexed",
    )

    with factory() as session:
        result = conversation_service.delete_conversation(session, owner.id, conversation.id)
    assert result.status == "deleted"
    assert result.cleanup_status == "pending"

    with factory() as session:
        stored_memory = memory_repository.get_owned(memory.id, owner.id, include_deleted=True)
        stored_conversation = session.get(ChatbotConversation, conversation.id)
        job = session.scalar(select(ChatbotJob).where(ChatbotJob.kind == "cleanup_conversation"))
    assert stored_memory is not None and stored_memory.status == "deleted"
    assert stored_memory.embedding_status == "deleted"
    assert stored_conversation is not None and stored_conversation.cleanup_status == "pending"
    assert job is not None

    semantic_index = FakeSemanticIndex()
    cleanup_service = CleanupService(
        session_factory=factory,
        short_term_memory=ShortTermMemoryService(factory, settings=settings),
        settings=settings,
        semantic_index=semantic_index,
    )
    runner = JobRunner(
        repository=repository,
        memory_service=SimpleNamespace(),
        short_term_memory=SimpleNamespace(),
        conversation_summary=SimpleNamespace(),
        title_service=SimpleNamespace(),
        cleanup_service=cleanup_service,
        settings=settings,
    )

    runner.run_once(limit=10)
    with factory() as session:
        stored_conversation = session.get(ChatbotConversation, conversation.id)
    assert stored_conversation is not None and stored_conversation.cleanup_status == "retry"

    semantic_index.fail_delete = False
    with factory() as session:
        session.execute(
            update(ChatbotJob)
            .where(ChatbotJob.id == job.id)
            .values(available_at=stored_conversation.updated_at)
        )
        session.commit()
    runner.run_once(limit=10)
    with factory() as session:
        stored_conversation = session.get(ChatbotConversation, conversation.id)
    assert stored_conversation is not None and stored_conversation.cleanup_status == "completed"
    assert semantic_index.deleted == [memory.id]
