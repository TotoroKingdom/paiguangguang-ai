from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.llm.provider import ChatCompletionRequest, ChatCompletionResult, ChatCompletionUsage, LLMMessage
from app.chatbot.repositories.conversation_repository import ConversationRepository
from app.chatbot.services.chat_service import ChatService
from app.chatbot.services.concurrency_service import ConcurrencyLease, ConcurrencyService
from app.core.config import Settings
from app.core.errors import ServiceRateLimitError
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


class _FakeRedisClient:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def ping(self) -> None:
        return None

    def set(self, key: str, value: str, *, nx: bool = False, px: int | None = None):  # noqa: ARG002
        if nx and key in self.values:
            return False
        self.values[key] = value
        return True

    def get(self, key: str):
        return self.values.get(key)

    def delete(self, key: str):
        self.values.pop(key, None)
        return 1

    def eval(self, script: str, numkeys: int, key: str, token: str, ttl_ms: str | None = None):  # noqa: ARG002
        current = self.values.get(key)
        if "pexpire" in script:
            if current == token:
                return 1
            return 0
        if current == token:
            self.values.pop(key, None)
            return 1
        return 0


class _FakeRedisModule:
    def __init__(self) -> None:
        self.client = _FakeRedisClient()

    def from_url(self, redis_url: str, decode_responses: bool = True):  # noqa: ARG002
        return self.client


def _build_session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_engine(f"sqlite+pysqlite:///{(tmp_path / f'{uuid4()}.sqlite3').as_posix()}", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def _create_user(session: Session, *, email: str) -> User:
    user = User(email=email, display_name=email.split("@")[0].title(), hashed_password="hashed-password")
    session.add(user)
    session.flush()
    return user


def test_concurrency_service_supports_owner_tokens_and_renewal() -> None:
    fake_redis = _FakeRedisModule()
    service = ConcurrencyService(
        Settings(redis_url="redis://localhost:6379/0", chatbot_lock_ttl_seconds=5),
        redis_module=fake_redis,
    )

    lease = service.acquire("conversation-1", "user-1")
    assert lease is not None
    assert lease.backend == "redis"

    second = service.acquire("conversation-1", "user-1")
    assert second is None

    assert service.renew(lease) is True
    assert service.release(lease) is True

    relocked = service.acquire("conversation-1", "user-1")
    assert relocked is not None
    wrong_token = ConcurrencyLease(
        conversation_id="conversation-1",
        user_id="user-1",
        owner_token="not-the-owner",
        acquired_at=lease.acquired_at,
        expires_at=lease.expires_at,
        backend=lease.backend,
    )
    assert service.renew(wrong_token) is False
    assert service.release(wrong_token) is False


def test_chat_service_applies_user_and_conversation_rate_limit(tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    conversation_repo = ConversationRepository(session_factory)
    fake_llm = FakeLLMClient(
        outcomes=[
            ChatCompletionResult(
                request_id="00000000-0000-0000-0000-000000000911",
                prompt_version="v1",
                model="deepseek-chat",
                message=LLMMessage(role="assistant", content="first answer"),
                finish_reason="stop",
                usage=ChatCompletionUsage(prompt_tokens=1, completion_tokens=2, total_tokens=3),
            ),
            ChatCompletionResult(
                request_id="00000000-0000-0000-0000-000000000912",
                prompt_version="v1",
                model="deepseek-chat",
                message=LLMMessage(role="assistant", content="second answer"),
                finish_reason="stop",
                usage=ChatCompletionUsage(prompt_tokens=1, completion_tokens=2, total_tokens=3),
            ),
        ]
    )
    service = ChatService(
        session_factory=session_factory,
        llm_client=fake_llm,
        settings=Settings(
            chatbot_default_model="deepseek-chat",
            chatbot_allowed_models=["deepseek-chat"],
            chatbot_message_max_chars=4000,
            chatbot_recent_message_limit=20,
            chatbot_rate_limit_max_requests=1,
            chatbot_rate_limit_window_seconds=60,
        ),
    )

    with session_factory() as session:
        owner = _create_user(session, email="owner@example.com")
        session.commit()

    conversation = conversation_repo.create(owner.id, "Thread", "deepseek-chat", system_prompt_version="v1")

    first = service.complete(
        owner.id,
        conversation.id,
        "How do we deploy this?",
        "00000000-0000-0000-0000-000000000913",
    )
    assert first.replayed is False

    with pytest.raises(ServiceRateLimitError):
        service.complete(
            owner.id,
            conversation.id,
            "How do we deploy this again?",
            "00000000-0000-0000-0000-000000000914",
        )
