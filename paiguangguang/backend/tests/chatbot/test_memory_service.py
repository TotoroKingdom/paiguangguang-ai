from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.errors import ChatbotApiError
from app.chatbot.llm.provider import ChatCompletionRequest, ChatCompletionResult, ChatCompletionUsage, LLMMessage
from app.chatbot.memory.memory_extractor import MemoryExtractor
from app.chatbot.models.memory import ChatbotMemory
from app.chatbot.repositories.conversation_repository import ConversationRepository
from app.chatbot.repositories.memory_repository import MemoryRepository
from app.chatbot.repositories.message_repository import MessageRepository
from app.chatbot.services.memory_service import MemoryService
from app.core.config import Settings
from app.db.base import Base
from app.db.models import User


@dataclass
class FakeLLMClient:
    outcomes: list[ChatCompletionResult] = field(default_factory=list)
    complete_calls: list[ChatCompletionRequest] = field(default_factory=list)

    def complete(self, request: ChatCompletionRequest) -> ChatCompletionResult:
        self.complete_calls.append(request)
        if not self.outcomes:
            raise AssertionError("Unexpected LLM call")
        return self.outcomes.pop(0)

    def close(self) -> None:
        return None


@dataclass
class FakeSemanticIndex:
    enabled: bool = True
    fail_on_upsert: bool = False
    upsert_calls: list[str] = field(default_factory=list)
    delete_calls: list[str] = field(default_factory=list)

    def upsert_memory(self, record) -> None:
        self.upsert_calls.append(record.id)
        if self.fail_on_upsert:
            raise RuntimeError("semantic index write failed")

    def delete_memory(self, memory_id: str) -> None:
        self.delete_calls.append(memory_id)


def _build_session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_engine(f"sqlite+pysqlite:///{(tmp_path / f'{uuid4()}.sqlite3').as_posix()}", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def _create_user(session: Session, *, email: str) -> User:
    user = User(email=email, display_name=email.split("@")[0].title(), hashed_password="hashed-password")
    session.add(user)
    session.flush()
    return user


def _build_service(
    session_factory: sessionmaker[Session],
    llm_client: FakeLLMClient | None = None,
    *,
    long_term_enabled: bool = True,
    semantic_enabled: bool = False,
    semantic_index: FakeSemanticIndex | None = None,
) -> MemoryService:
    return MemoryService(
        session_factory=session_factory,
        extractor=MemoryExtractor(
            llm_client=llm_client,
            settings=Settings(
                chatbot_default_model="deepseek-chat",
                chatbot_memory_min_confidence=0.75,
                chatbot_long_term_memory_enabled=long_term_enabled,
                chatbot_semantic_memory_enabled=semantic_enabled,
            ),
        ),
        settings=Settings(
            chatbot_default_model="deepseek-chat",
            chatbot_memory_min_confidence=0.75,
            chatbot_long_term_memory_enabled=long_term_enabled,
            chatbot_semantic_memory_enabled=semantic_enabled,
        ),
        semantic_index=semantic_index,
    )


def _seed_turn(
    session_factory: sessionmaker[Session],
    owner_id: str,
    conversation_id: str,
    *,
    user_content: str,
    assistant_content: str = "好的。",
    client_request_id: str | None = None,
) -> tuple[str, str]:
    message_repo = MessageRepository(session_factory)
    user_message, assistant_message = message_repo.create_user_and_assistant(
        conversation_id,
        owner_id,
        content=user_content,
        client_request_id=client_request_id or str(uuid4()),
        assistant_model="deepseek-chat",
    )
    message_repo.finalize(
        assistant_message.id,
        owner_id,
        expected_status="pending",
        status="completed",
        content=assistant_content,
        model="deepseek-chat",
        prompt_tokens=5,
        completion_tokens=7,
        total_tokens=12,
    )
    return user_message.id, assistant_message.id


def test_memory_service_creates_active_memory_and_supersedes_previous_active(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    conversation_repo = ConversationRepository(session_factory)
    memory_repo = MemoryRepository(session_factory)
    service = _build_service(session_factory)

    with session_factory() as session:
        owner = _create_user(session, email="owner@example.com")
        session.commit()

    conversation = conversation_repo.create(owner.id, "Thread", "deepseek-chat", system_prompt_version="v1")
    first_user_id, first_assistant_id = _seed_turn(
        session_factory,
        owner.id,
        conversation.id,
        user_content="请记住我的项目名是星轨",
    )
    second_user_id, second_assistant_id = _seed_turn(
        session_factory,
        owner.id,
        conversation.id,
        user_content="请记住我的项目名是天枢",
    )

    first_created = service.process_completed_turn(
        owner.id,
        conversation.id,
        first_user_id,
        first_assistant_id,
    )
    second_created = service.process_completed_turn(
        owner.id,
        conversation.id,
        second_user_id,
        second_assistant_id,
    )

    assert len(first_created) == 1
    assert first_created[0].status == "active"
    assert len(second_created) == 1
    assert second_created[0].status == "active"
    assert second_created[0].memory_type == "project_context"

    active_items = memory_repo.list_owned(owner.id, status="active")
    superseded_items = memory_repo.list_owned(owner.id, status="superseded")

    assert [item.id for item in active_items] == [second_created[0].id]
    assert [item.id for item in superseded_items] == [first_created[0].id]


def test_memory_service_keeps_low_confidence_items_candidate_and_rejects_sensitive_input(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    conversation_repo = ConversationRepository(session_factory)
    memory_repo = MemoryRepository(session_factory)
    fake_llm = FakeLLMClient(
        outcomes=[
            ChatCompletionResult(
                request_id="00000000-0000-0000-0000-000000000401",
                prompt_version="memory-v1",
                model="deepseek-chat",
                message=LLMMessage(
                    role="assistant",
                    content=(
                        '[{"action":"upsert","memory_type":"preference","content":"我喜欢深色主题",'
                        '"confidence":0.42,"importance":0.2,"status":"candidate"}]'
                    ),
                ),
                finish_reason="stop",
                usage=ChatCompletionUsage(prompt_tokens=13, completion_tokens=21, total_tokens=34),
            )
        ]
    )
    service = _build_service(session_factory, fake_llm)

    with session_factory() as session:
        owner = _create_user(session, email="owner@example.com")
        session.commit()

    conversation = conversation_repo.create(owner.id, "Thread", "deepseek-chat", system_prompt_version="v1")
    low_user_id, low_assistant_id = _seed_turn(
        session_factory,
        owner.id,
        conversation.id,
        user_content="这条偏好要保留：界面尽量保持深色主题",
    )
    sensitive_user_id, sensitive_assistant_id = _seed_turn(
        session_factory,
        owner.id,
        conversation.id,
        user_content="请记住我的密码是secret-123",
    )

    candidate_created = service.process_completed_turn(
        owner.id,
        conversation.id,
        low_user_id,
        low_assistant_id,
    )
    rejected_created = service.process_completed_turn(
        owner.id,
        conversation.id,
        sensitive_user_id,
        sensitive_assistant_id,
    )

    assert len(candidate_created) == 1
    assert candidate_created[0].status == "candidate"
    assert candidate_created[0].confidence == 0.42
    assert rejected_created == []
    assert fake_llm.complete_calls
    assert [item.id for item in memory_repo.list_owned(owner.id, status="candidate")] == [candidate_created[0].id]


def test_memory_service_rejects_foreign_source_messages(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    conversation_repo = ConversationRepository(session_factory)
    service = _build_service(session_factory)

    with session_factory() as session:
        owner = _create_user(session, email="owner@example.com")
        foreign = _create_user(session, email="foreign@example.com")
        session.commit()

    conversation = conversation_repo.create(owner.id, "Thread", "deepseek-chat", system_prompt_version="v1")
    foreign_conversation = conversation_repo.create(foreign.id, "Foreign", "deepseek-chat", system_prompt_version="v1")
    source_user_id, source_assistant_id = _seed_turn(
        session_factory,
        foreign.id,
        foreign_conversation.id,
        user_content="请记住我的项目名是别人的项目",
    )

    with pytest.raises(ChatbotApiError) as exc:
        service.process_completed_turn(
            owner.id,
            conversation.id,
            source_user_id,
            source_assistant_id,
            source_message_ids=[source_user_id, source_assistant_id],
        )

    assert exc.value.code == "CHATBOT_MESSAGE_NOT_FOUND"

    with session_factory() as session:
        assert session.query(ChatbotMemory).count() == 0


def test_memory_service_syncs_semantic_index_and_marks_embedding_status(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    conversation_repo = ConversationRepository(session_factory)
    memory_repo = MemoryRepository(session_factory)
    fake_semantic_index = FakeSemanticIndex()
    service = _build_service(
        session_factory,
        semantic_index=fake_semantic_index,
        semantic_enabled=True,
    )

    with session_factory() as session:
        owner = _create_user(session, email="owner@example.com")
        session.commit()

    conversation = conversation_repo.create(owner.id, "Thread", "deepseek-chat", system_prompt_version="v1")
    user_message_id, assistant_message_id = _seed_turn(
        session_factory,
        owner.id,
        conversation.id,
        user_content="请记住我的项目名是星轨",
    )

    created = service.process_completed_turn(
        owner.id,
        conversation.id,
        user_message_id,
        assistant_message_id,
    )

    assert len(created) == 1
    assert created[0].status == "active"
    assert fake_semantic_index.upsert_calls == [created[0].id]
    assert memory_repo.get_owned(created[0].id, owner.id).embedding_status == "indexed"

    with session_factory() as session:
        deleted = service.delete_memory(session, owner.id, created[0].id)

    assert deleted.status == "deleted"
    assert deleted.cleanup_status == "pending"
    assert fake_semantic_index.delete_calls == []
    assert memory_repo.get_owned(created[0].id, owner.id, include_deleted=True).embedding_status == "deleted"


def test_memory_service_keeps_db_write_when_semantic_index_fails(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    conversation_repo = ConversationRepository(session_factory)
    memory_repo = MemoryRepository(session_factory)
    fake_semantic_index = FakeSemanticIndex(fail_on_upsert=True)
    service = _build_service(
        session_factory,
        semantic_index=fake_semantic_index,
        semantic_enabled=True,
    )

    with session_factory() as session:
        owner = _create_user(session, email="owner@example.com")
        session.commit()

    conversation = conversation_repo.create(owner.id, "Thread", "deepseek-chat", system_prompt_version="v1")
    user_message_id, assistant_message_id = _seed_turn(
        session_factory,
        owner.id,
        conversation.id,
        user_content="请记住我的项目名是天枢",
    )

    created = service.process_completed_turn(
        owner.id,
        conversation.id,
        user_message_id,
        assistant_message_id,
    )

    assert len(created) == 1
    assert created[0].status == "active"
    assert fake_semantic_index.upsert_calls == [created[0].id]
    assert memory_repo.get_owned(created[0].id, owner.id).embedding_status == "failed"
