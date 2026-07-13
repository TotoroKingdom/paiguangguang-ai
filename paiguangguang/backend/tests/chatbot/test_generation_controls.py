from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass, field
from pathlib import Path
from queue import Queue
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.llm.provider import ChatCompletionRequest, ChatCompletionUsage, LLMStreamEvent
from app.chatbot.models.conversation import ChatbotConversation
from app.chatbot.models.message import ChatbotMessage
from app.chatbot.repositories.conversation_repository import ConversationRepository
from app.chatbot.repositories.llm_run_repository import LLMRunRepository
from app.chatbot.repositories.message_repository import MessageRepository
from app.chatbot.services.cancellation_service import CancellationService, get_cancellation_service
from app.chatbot.services.chat_service import ChatService, get_chat_service
from app.chatbot.services.stream_service import ChatStreamService, get_chat_stream_service
from app.core.config import Settings
from app.db.base import Base
from app.db.models import User
from app.db.session import get_db_session
from app.main import app as fastapi_app
from app.services.auth import AuthService, get_auth_service


@dataclass
class FakeLLMClient:
    outcomes: list[object] = field(default_factory=list)
    stream_calls: list[ChatCompletionRequest] = field(default_factory=list)

    def stream(self, request: ChatCompletionRequest):
        self.stream_calls.append(request)
        if not self.outcomes:
            raise AssertionError("Unexpected LLM call")
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        yield from outcome

    def close(self) -> None:
        return None


def _build_session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_engine(f"sqlite+pysqlite:///{(tmp_path / f'{uuid4()}.sqlite3').as_posix()}", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def _create_user(session: Session, auth_service: AuthService, *, email: str) -> User:
    return auth_service.create_user(
        session,
        email=email,
        display_name=email.split("@")[0].title(),
        password="Secret123!Strong",
        is_active=True,
    )


def _build_services(session_factory: sessionmaker[Session], fake_llm: FakeLLMClient):
    settings = Settings(
        chatbot_default_model="deepseek-chat",
        chatbot_allowed_models=["deepseek-chat"],
        chatbot_message_max_chars=4000,
        chatbot_recent_message_limit=20,
    )
    chat_service = ChatService(session_factory=session_factory, llm_client=fake_llm, settings=settings)
    cancellation_service = CancellationService(settings=settings)
    stream_service = ChatStreamService(
        chat_service=chat_service,
        cancellation_service=cancellation_service,
        settings=settings,
    )
    return chat_service, cancellation_service, stream_service


def _build_test_app(
    session: Session,
    auth_service: AuthService,
    chat_service: ChatService,
    stream_service: ChatStreamService,
    cancellation_service: CancellationService,
) -> FastAPI:
    app = fastapi_app
    app.dependency_overrides.clear()

    def override_db_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_chat_service] = lambda: chat_service
    app.dependency_overrides[get_chat_stream_service] = lambda: stream_service
    app.dependency_overrides[get_cancellation_service] = lambda: cancellation_service
    return app


def _seed_completed_turn(session_factory: sessionmaker[Session], owner_id: str, conversation_id: str) -> tuple[str, str]:
    message_repo = MessageRepository(session_factory)
    llm_run_repo = LLMRunRepository(session_factory)
    user_request_id = str(uuid4())
    run_request_id = str(uuid4())
    user_message, assistant_message = message_repo.create_user_and_assistant(
        conversation_id,
        owner_id,
        content="previous user message",
        client_request_id=user_request_id,
        assistant_model="deepseek-chat",
    )
    llm_run = llm_run_repo.create(
        request_id=run_request_id,
        user_id=owner_id,
        conversation_id=conversation_id,
        message_id=assistant_message.id,
        provider="deepseek",
        model="deepseek-chat",
        prompt_version="v1",
    )
    message_repo.finalize(
        assistant_message.id,
        owner_id,
        expected_status="pending",
        status="completed",
        content="previous assistant message",
        model="deepseek-chat",
        prompt_tokens=5,
        completion_tokens=7,
        total_tokens=12,
    )
    llm_run_repo.finalize(
        llm_run.id,
        owner_id,
        expected_status="pending",
        status="completed",
        prompt_tokens=5,
        completion_tokens=7,
        total_tokens=12,
        finish_reason="stop",
    )
    return user_message.id, assistant_message.id


def _seed_failed_turn(session_factory: sessionmaker[Session], owner_id: str, conversation_id: str) -> tuple[str, str]:
    message_repo = MessageRepository(session_factory)
    llm_run_repo = LLMRunRepository(session_factory)
    user_request_id = str(uuid4())
    run_request_id = str(uuid4())
    user_message, assistant_message = message_repo.create_user_and_assistant(
        conversation_id,
        owner_id,
        content="retry me",
        client_request_id=user_request_id,
        assistant_model="deepseek-chat",
    )
    llm_run = llm_run_repo.create(
        request_id=run_request_id,
        user_id=owner_id,
        conversation_id=conversation_id,
        message_id=assistant_message.id,
        provider="deepseek",
        model="deepseek-chat",
        prompt_version="v1",
    )
    message_repo.finalize(
        assistant_message.id,
        owner_id,
        expected_status="pending",
        status="failed",
        content="partial answer",
        model="deepseek-chat",
        prompt_tokens=3,
        completion_tokens=2,
        total_tokens=5,
        error_code="CHATBOT_LLM_TIMEOUT",
    )
    llm_run_repo.finalize(
        llm_run.id,
        owner_id,
        expected_status="pending",
        status="failed",
        prompt_tokens=3,
        completion_tokens=2,
        total_tokens=5,
        error_code="CHATBOT_LLM_TIMEOUT",
        error_message="LLM request timed out",
    )
    return user_message.id, assistant_message.id


def test_stream_completion_honors_pre_requested_cancellation(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-for-chatbot-api-strong")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")

    session_factory = _build_session_factory(tmp_path)
    session = session_factory()
    auth_service = AuthService()
    fake_llm = FakeLLMClient(
        outcomes=[
            [
                LLMStreamEvent(
                    kind="delta",
                    request_id="00000000-0000-0000-0000-000000000311",
                    prompt_version="v1",
                    model="deepseek-chat",
                    content="should not persist",
                ),
                LLMStreamEvent(
                    kind="completed",
                    request_id="00000000-0000-0000-0000-000000000311",
                    prompt_version="v1",
                    model="deepseek-chat",
                    content="ignored",
                    finish_reason="stop",
                    usage=ChatCompletionUsage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
                ),
            ]
        ]
    )
    chat_service, cancellation_service, stream_service = _build_services(session_factory, fake_llm)

    with session_factory() as seed_session:
        owner = _create_user(seed_session, auth_service, email="owner@example.com")
        seed_session.commit()

    conversation = ConversationRepository(session_factory).create(owner.id, "Thread", "deepseek-chat", system_prompt_version="v1")
    with session_factory() as seed_session:
        conversation_row = seed_session.get(ChatbotConversation, conversation.id)
        if conversation_row is None:
            raise AssertionError("Conversation row not found")
        accepted = chat_service._accept_turn(
            seed_session,
            user_id=owner.id,
            conversation=conversation_row,
            content="Check cancellation",
            client_request_id="00000000-0000-0000-0000-000000000311",
        )
        seed_session.commit()
    cancellation_service.request_stop(accepted.conversation_id, accepted.assistant_message_id)

    request = chat_service._build_request(accepted, "Check cancellation")
    queue: Queue = Queue()
    stream_service._produce_stream_events(queue, accepted, owner.id, request)

    events = []
    while True:
        item = queue.get()
        if item is None:
            break
        events.append(item.event)

    assert events == ["message.cancelled", "usage.updated", "stream.end"]
    assert len(fake_llm.stream_calls) == 1


def test_stop_generation_marks_cancellation_request(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-for-chatbot-api-strong")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")

    session_factory = _build_session_factory(tmp_path)
    session = session_factory()
    auth_service = AuthService()
    fake_llm = FakeLLMClient()
    chat_service, cancellation_service, stream_service = _build_services(session_factory, fake_llm)

    with session_factory() as seed_session:
        owner = _create_user(seed_session, auth_service, email="owner@example.com")
        seed_session.commit()

    conversation = ConversationRepository(session_factory).create(owner.id, "Thread", "deepseek-chat", system_prompt_version="v1")
    with session_factory() as seed_session:
        conversation_row = seed_session.get(ChatbotConversation, conversation.id)
        if conversation_row is None:
            raise AssertionError("Conversation row not found")
        accepted = chat_service._accept_turn(
            seed_session,
            user_id=owner.id,
            conversation=conversation_row,
            content="Please stop",
            client_request_id="00000000-0000-0000-0000-000000000411",
        )
        seed_session.commit()

    app = _build_test_app(session, auth_service, chat_service, stream_service, cancellation_service)
    client = TestClient(app)

    try:
        login_response = client.post("/api/v1/auth/login", json={"email": owner.email, "password": "Secret123!Strong"})
        headers = {"Authorization": f"Bearer {login_response.json()['data']['access_token']}"}

        response = client.post(
            f"/api/v1/chatbot/conversations/{conversation.id}/stop",
            headers=headers,
            json={"assistant_message_id": accepted.assistant_message_id},
        )

        assert response.status_code == 202
        body = response.json()["data"]
        assert body["status"] == "cancellation_requested"
        assert cancellation_service.is_requested(conversation.id, accepted.assistant_message_id)
    finally:
        app.dependency_overrides.clear()
        session.close()


def test_retry_message_creates_variant_and_replays_duplicate_requests(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-for-chatbot-api-strong")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")

    session_factory = _build_session_factory(tmp_path)
    session = session_factory()
    auth_service = AuthService()
    fake_llm = FakeLLMClient(
        outcomes=[
            [
                LLMStreamEvent(
                    kind="delta",
                    request_id="00000000-0000-0000-0000-000000000411",
                    prompt_version="v1",
                    model="deepseek-chat",
                    content="retry answer",
                ),
                LLMStreamEvent(
                    kind="completed",
                    request_id="00000000-0000-0000-0000-000000000411",
                    prompt_version="v1",
                    model="deepseek-chat",
                    content="retry answer",
                    finish_reason="stop",
                    usage=ChatCompletionUsage(prompt_tokens=4, completion_tokens=6, total_tokens=10),
                ),
            ]
        ]
    )
    chat_service, cancellation_service, stream_service = _build_services(session_factory, fake_llm)

    with session_factory() as seed_session:
        owner = _create_user(seed_session, auth_service, email="owner@example.com")
        seed_session.commit()

    conversation = ConversationRepository(session_factory).create(owner.id, "Thread", "deepseek-chat", system_prompt_version="v1")
    _, assistant_message_id = _seed_failed_turn(session_factory, owner.id, conversation.id)

    app = _build_test_app(session, auth_service, chat_service, stream_service, cancellation_service)
    client = TestClient(app)

    try:
        login_response = client.post("/api/v1/auth/login", json={"email": owner.email, "password": "Secret123!Strong"})
        headers = {"Authorization": f"Bearer {login_response.json()['data']['access_token']}"}

        first_response = client.post(
            f"/api/v1/chatbot/conversations/{conversation.id}/messages/{assistant_message_id}/retry",
            headers={**headers, "Idempotency-Key": "00000000-0000-0000-0000-000000000411"},
            json={"client_request_id": "00000000-0000-0000-0000-000000000411"},
        )
        assert first_response.status_code == 200
        assert "event: message.created" in first_response.text
        assert '"replayed":false' in first_response.text

        duplicate_response = client.post(
            f"/api/v1/chatbot/conversations/{conversation.id}/messages/{assistant_message_id}/retry",
            headers={**headers, "Idempotency-Key": "00000000-0000-0000-0000-000000000411"},
            json={"client_request_id": "00000000-0000-0000-0000-000000000411"},
        )
        assert duplicate_response.status_code == 200
        assert '"replayed":true' in duplicate_response.text
        assert len(fake_llm.stream_calls) == 1

        with session_factory() as verify_session:
            message_count = verify_session.scalar(
                select(func.count()).select_from(ChatbotMessage).where(
                    ChatbotMessage.conversation_id == conversation.id,
                    ChatbotMessage.user_id == owner.id,
                )
            )
            assert message_count is not None and message_count >= 3
    finally:
        app.dependency_overrides.clear()
        session.close()


def test_regenerate_rejects_non_latest_turn(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-for-chatbot-api-strong")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")

    session_factory = _build_session_factory(tmp_path)
    session = session_factory()
    auth_service = AuthService()
    fake_llm = FakeLLMClient()
    chat_service, cancellation_service, stream_service = _build_services(session_factory, fake_llm)

    with session_factory() as seed_session:
        owner = _create_user(seed_session, auth_service, email="owner@example.com")
        seed_session.commit()

    conversation = ConversationRepository(session_factory).create(owner.id, "Thread", "deepseek-chat", system_prompt_version="v1")
    _, first_assistant_id = _seed_completed_turn(session_factory, owner.id, conversation.id)
    _seed_completed_turn(session_factory, owner.id, conversation.id)

    app = _build_test_app(session, auth_service, chat_service, stream_service, cancellation_service)
    client = TestClient(app)

    try:
        login_response = client.post("/api/v1/auth/login", json={"email": owner.email, "password": "Secret123!Strong"})
        headers = {"Authorization": f"Bearer {login_response.json()['data']['access_token']}"}

        response = client.post(
            f"/api/v1/chatbot/conversations/{conversation.id}/messages/{first_assistant_id}/regenerate",
            headers={**headers, "Idempotency-Key": "00000000-0000-0000-0000-000000000511"},
            json={"client_request_id": "00000000-0000-0000-0000-000000000511"},
        )

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "CHATBOT_REGENERATE_NOT_LATEST_TURN"
    finally:
        app.dependency_overrides.clear()
        session.close()
