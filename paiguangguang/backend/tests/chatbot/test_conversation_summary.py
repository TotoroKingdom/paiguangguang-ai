from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.llm.exceptions import LLMTimeoutError
from app.chatbot.llm.provider import ChatCompletionRequest, ChatCompletionResult, ChatCompletionUsage, LLMMessage
from app.chatbot.memory.conversation_summary import ConversationSummaryService
from app.chatbot.memory.short_term_memory import ShortTermMemoryService
from app.chatbot.models.conversation import ChatbotConversation, ChatbotConversationSummary
from app.chatbot.repositories.conversation_repository import ConversationRepository
from app.chatbot.repositories.message_repository import MessageRepository
from app.core.config import Settings
from app.db.base import Base
from app.db.models import User


@dataclass
class FakeLLMClient:
    outcomes: list[ChatCompletionResult | Exception] = field(default_factory=list)
    complete_calls: list[ChatCompletionRequest] = field(default_factory=list)

    def complete(self, request: ChatCompletionRequest) -> ChatCompletionResult:
        self.complete_calls.append(request)
        if not self.outcomes:
            raise AssertionError("Unexpected LLM call")
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def close(self) -> None:
        return None


def _build_session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_engine(f"sqlite+pysqlite:///{(tmp_path / f'{uuid4()}.sqlite3').as_posix()}", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def _create_user(session: Session, *, email: str) -> User:
    user = User(email=email, display_name=email.split("@")[0].title(), hashed_password="hashed-password")
    session.add(user)
    session.flush()
    return user


def _build_settings() -> Settings:
    return Settings(
        chatbot_env="development",
        chatbot_default_model="deepseek-chat",
        chatbot_summary_model="deepseek-chat",
        chatbot_summary_prompt_version="summary-v1",
        chatbot_summary_message_threshold=20,
        chatbot_summary_token_ratio=0.60,
        chatbot_context_token_budget=8000,
        chatbot_recent_message_limit=20,
        chatbot_message_max_chars=4000,
        chatbot_allowed_models=["deepseek-chat"],
    )


def _seed_completed_turns(
    session_factory: sessionmaker[Session],
    owner_id: str,
    conversation_id: str,
    *,
    turn_count: int,
    start_index: int = 1,
    token_value: int = 1,
) -> None:
    message_repo = MessageRepository(session_factory)
    for index in range(turn_count):
        turn_number = start_index + index
        _, assistant_message = message_repo.create_user_and_assistant(
            conversation_id,
            owner_id,
            content=f"user-{turn_number}",
            client_request_id=f"00000000-0000-0000-0000-00000000{turn_number:04d}",
            assistant_model="deepseek-chat",
        )
        message_repo.finalize(
            assistant_message.id,
            owner_id,
            expected_status="pending",
            status="completed",
            content=f"assistant-{turn_number}",
            model="deepseek-chat",
            prompt_tokens=token_value,
            completion_tokens=token_value,
            total_tokens=token_value * 2,
        )


def _build_services(session_factory: sessionmaker[Session], llm_client: FakeLLMClient):
    settings = _build_settings()
    summary_service = ConversationSummaryService(
        session_factory=session_factory,
        llm_client=llm_client,
        settings=settings,
    )
    memory_service = ShortTermMemoryService(session_factory=session_factory, settings=settings)
    return summary_service, memory_service


def test_conversation_summary_generates_continuous_versions_and_refreshes_short_term_memory(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    fake_llm = FakeLLMClient(
        outcomes=[
            ChatCompletionResult(
                request_id="00000000-0000-0000-0000-000000001111",
                prompt_version="summary-v1",
                model="deepseek-chat",
                message=LLMMessage(role="assistant", content="summary-1"),
                finish_reason="stop",
                usage=ChatCompletionUsage(prompt_tokens=7, completion_tokens=8, total_tokens=15),
            ),
            ChatCompletionResult(
                request_id="00000000-0000-0000-0000-000000002222",
                prompt_version="summary-v1",
                model="deepseek-chat",
                message=LLMMessage(role="assistant", content="summary-2"),
                finish_reason="stop",
                usage=ChatCompletionUsage(prompt_tokens=9, completion_tokens=10, total_tokens=19),
            ),
        ]
    )
    summary_service, memory_service = _build_services(session_factory, fake_llm)

    with session_factory() as session:
        owner = _create_user(session, email="owner@example.com")
        session.commit()

    conversation_repo = ConversationRepository(session_factory)
    conversation = conversation_repo.create(owner.id, "Thread", "deepseek-chat", system_prompt_version="v1")

    _seed_completed_turns(session_factory, owner.id, conversation.id, turn_count=20)

    first_summary = summary_service.maybe_generate_summary(owner.id, conversation.id)
    assert first_summary is not None
    assert first_summary.summary_version == 1
    assert first_summary.start_sequence == 1
    assert first_summary.end_sequence == 20
    assert first_summary.status == "completed"
    assert first_summary.summary == "summary-1"

    with session_factory() as session:
        snapshot = memory_service.load_context(session, owner.id, conversation.id)
    assert snapshot.summary == "summary-1"
    assert [message.content for message in snapshot.recent_messages] == [
        item
        for i in range(11, 21)
        for item in (f"user-{i}", f"assistant-{i}")
    ]

    _seed_completed_turns(session_factory, owner.id, conversation.id, turn_count=10, start_index=21)

    second_summary = summary_service.maybe_generate_summary(owner.id, conversation.id)
    assert second_summary is not None
    assert second_summary.summary_version == 2
    assert second_summary.start_sequence == 21
    assert second_summary.end_sequence == 40
    assert second_summary.status == "completed"
    assert second_summary.summary == "summary-2"

    with session_factory() as session:
        snapshot = memory_service.load_context(session, owner.id, conversation.id)
    assert snapshot.summary == "summary-2"
    assert [message.content for message in snapshot.recent_messages] == [
        item
        for i in range(21, 31)
        for item in (f"user-{i}", f"assistant-{i}")
    ]

    assert [call.prompt_version for call in fake_llm.complete_calls] == ["summary-v1", "summary-v1"]
    assert [call.model for call in fake_llm.complete_calls] == ["deepseek-chat", "deepseek-chat"]
    assert "summary-1" in fake_llm.complete_calls[1].messages[1].content


def test_conversation_summary_failure_keeps_latest_completed_summary(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    fake_llm = FakeLLMClient(
        outcomes=[
            ChatCompletionResult(
                request_id="00000000-0000-0000-0000-000000003333",
                prompt_version="summary-v1",
                model="deepseek-chat",
                message=LLMMessage(role="assistant", content="summary-1"),
                finish_reason="stop",
                usage=ChatCompletionUsage(prompt_tokens=4, completion_tokens=5, total_tokens=9),
            ),
            LLMTimeoutError("summary timed out"),
        ]
    )
    summary_service, memory_service = _build_services(session_factory, fake_llm)

    with session_factory() as session:
        owner = _create_user(session, email="owner@example.com")
        session.commit()

    conversation_repo = ConversationRepository(session_factory)
    conversation = conversation_repo.create(owner.id, "Thread", "deepseek-chat", system_prompt_version="v1")

    _seed_completed_turns(session_factory, owner.id, conversation.id, turn_count=20)
    first_summary = summary_service.maybe_generate_summary(owner.id, conversation.id)
    assert first_summary is not None
    assert first_summary.status == "completed"

    _seed_completed_turns(session_factory, owner.id, conversation.id, turn_count=10, start_index=21)
    failed_summary = summary_service.maybe_generate_summary(owner.id, conversation.id)
    assert failed_summary is not None
    assert failed_summary.summary_version == 2
    assert failed_summary.status == "failed"
    assert failed_summary.summary == ""

    with session_factory() as session:
        latest_completed = session.scalar(
            select(ChatbotConversationSummary)
            .where(
                ChatbotConversationSummary.conversation_id == conversation.id,
                ChatbotConversationSummary.status == "completed",
            )
            .order_by(ChatbotConversationSummary.summary_version.desc())
        )
        snapshot = memory_service.load_context(session, owner.id, conversation.id)

    assert latest_completed is not None
    assert latest_completed.summary_version == 1
    assert snapshot.summary == "summary-1"
    assert [call.prompt_version for call in fake_llm.complete_calls] == ["summary-v1", "summary-v1"]
