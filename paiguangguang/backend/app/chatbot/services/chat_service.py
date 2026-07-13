from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter
from typing import Iterator
from uuid import UUID, uuid4

from sqlalchemy import desc, select
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.errors import ChatbotApiError
from app.chatbot.llm.client import LLMClient
from app.chatbot.llm.deepseek_provider import DeepSeekProvider
from app.chatbot.llm.exceptions import (
    LLMConfigurationError,
    LLMError,
    LLMProtocolError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from app.chatbot.llm.prompt_builder import PromptBuilder
from app.chatbot.llm.provider import ChatCompletionRequest, ChatCompletionResult, ChatCompletionUsage, LLMMessage
from app.chatbot.models.conversation import ChatbotConversation
from app.chatbot.models.llm_run import ChatbotLLMRun
from app.chatbot.models.message import ChatbotMessage
from app.chatbot.schemas.chat import ChatCompletionData, ChatLLMRunData
from app.chatbot.schemas.message import MessageData
from app.core.config import Settings, get_settings
from app.db.session import build_session_factory


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class _AcceptedTurn:
    conversation_id: str
    client_request_id: str
    user_message_id: str
    assistant_message_id: str
    llm_run_id: str
    model: str
    prompt_version: str
    history_messages: tuple[LLMMessage, ...]


class ChatService:
    def __init__(
        self,
        session_factory: sessionmaker[Session] | None = None,
        *,
        llm_client: LLMClient | None = None,
        settings: Settings | None = None,
        prompt_builder_factory: type[PromptBuilder] = PromptBuilder,
    ) -> None:
        self.settings = settings or get_settings()
        self.session_factory = session_factory or build_session_factory(self.settings)
        self._owns_llm_client = llm_client is None
        self.llm_client = llm_client or LLMClient(
            provider=DeepSeekProvider(settings=self.settings),
            settings=self.settings,
        )
        self._prompt_builder_factory = prompt_builder_factory

    def close(self) -> None:
        if self._owns_llm_client:
            self.llm_client.close()

    @contextmanager
    def _session(self) -> Iterator[Session]:
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def complete(
        self,
        user_id: str,
        conversation_id: str,
        content: str,
        client_request_id: str,
    ) -> ChatCompletionData:
        user_id = self._normalize_uuid(user_id, field_name="user_id")
        conversation_id = self._normalize_uuid(conversation_id, field_name="conversation_id")
        client_request_id = self._normalize_uuid(client_request_id, field_name="client_request_id")
        content = self._validate_content(content)

        with self._session() as session:
            replay = self._load_replay(session, user_id, conversation_id, client_request_id, content)
            if replay is not None:
                return replay

            conversation = session.scalar(
                select(ChatbotConversation)
                .where(
                    ChatbotConversation.id == conversation_id,
                    ChatbotConversation.user_id == user_id,
                    ChatbotConversation.deleted_at.is_(None),
                )
                .with_for_update()
            )
            if conversation is None:
                raise ChatbotApiError(
                    status_code=404,
                    code="CHATBOT_CONVERSATION_NOT_FOUND",
                    message="Conversation not found",
                )
            if conversation.status != "active":
                raise ChatbotApiError(
                    status_code=409,
                    code="CHATBOT_CONVERSATION_NOT_ACTIVE",
                    message="Conversation is not active",
                )

            active_run = session.scalar(
                select(ChatbotLLMRun)
                .where(
                    ChatbotLLMRun.conversation_id == conversation_id,
                    ChatbotLLMRun.user_id == user_id,
                    ChatbotLLMRun.status.in_(("pending", "streaming")),
                )
                .order_by(desc(ChatbotLLMRun.updated_at), desc(ChatbotLLMRun.id))
                .limit(1)
            )
            if active_run is not None:
                raise ChatbotApiError(
                    status_code=409,
                    code="CHATBOT_CONVERSATION_BUSY",
                    message="Conversation is busy",
                )

            accepted = self._accept_turn(
                session,
                user_id=user_id,
                conversation=conversation,
                content=content,
                client_request_id=client_request_id,
            )

        request = self._build_request(accepted, content)
        started_at = perf_counter()
        try:
            result = self.llm_client.complete(request)
        except (LLMTimeoutError, LLMRateLimitError, LLMProviderError, LLMProtocolError, LLMConfigurationError) as exc:
            return self._finalize_failed(accepted, user_id, exc, started_at)
        except LLMError as exc:
            return self._finalize_failed(accepted, user_id, exc, started_at)

        return self._finalize_completed(accepted, user_id, result, started_at)

    def _accept_turn(
        self,
        session: Session,
        *,
        user_id: str,
        conversation: ChatbotConversation,
        content: str,
        client_request_id: str,
    ) -> _AcceptedTurn:
        now = _utcnow()
        user_sequence = conversation.next_sequence
        assistant_sequence = user_sequence + 1
        conversation.next_sequence = assistant_sequence + 1
        conversation.last_message_at = now
        conversation.updated_at = now

        user_message_id = str(uuid4())
        assistant_message_id = str(uuid4())
        llm_run_id = str(uuid4())
        user_message = ChatbotMessage(
            id=user_message_id,
            conversation_id=conversation.id,
            user_id=user_id,
            role="user",
            content=content,
            content_json=None,
            sequence_number=user_sequence,
            status="completed",
            model=None,
            parent_message_id=None,
            client_request_id=client_request_id,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            error_code=None,
            created_at=now,
            updated_at=now,
        )
        assistant_message = ChatbotMessage(
            id=assistant_message_id,
            conversation_id=conversation.id,
            user_id=user_id,
            role="assistant",
            content="",
            content_json=None,
            sequence_number=assistant_sequence,
            status="pending",
            model=conversation.model,
            parent_message_id=user_message_id,
            client_request_id=None,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            error_code=None,
            created_at=now,
            updated_at=now,
        )
        llm_run = ChatbotLLMRun(
            id=llm_run_id,
            request_id=client_request_id,
            user_id=user_id,
            conversation_id=conversation.id,
            message_id=assistant_message_id,
            provider="deepseek",
            model=conversation.model,
            prompt_version=conversation.system_prompt_version,
            status="pending",
            attempt_count=1,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            latency_ms=None,
            first_token_latency_ms=None,
            finish_reason=None,
            error_code=None,
            error_message=None,
            started_at=None,
            completed_at=None,
            created_at=now,
            updated_at=now,
        )
        session.add_all([user_message, assistant_message, llm_run])
        session.flush()

        history_messages = self._load_recent_messages(
            session,
            user_id=user_id,
            conversation_id=str(conversation.id),
            before_sequence_number=user_sequence,
        )
        return _AcceptedTurn(
            conversation_id=str(conversation.id),
            client_request_id=client_request_id,
            user_message_id=user_message_id,
            assistant_message_id=assistant_message_id,
            llm_run_id=llm_run_id,
            model=conversation.model,
            prompt_version=conversation.system_prompt_version,
            history_messages=history_messages,
        )

    def _load_replay(
        self,
        session: Session,
        user_id: str,
        conversation_id: str,
        client_request_id: str,
        content: str,
    ) -> ChatCompletionData | None:
        existing_user_message = session.scalar(
            select(ChatbotMessage)
            .where(
                ChatbotMessage.conversation_id == conversation_id,
                ChatbotMessage.user_id == user_id,
                ChatbotMessage.client_request_id == client_request_id,
                ChatbotMessage.role == "user",
            )
            .limit(1)
        )
        if existing_user_message is None:
            return None
        if existing_user_message.content != content:
            raise ChatbotApiError(
                status_code=409,
                code="CHATBOT_REQUEST_CONFLICT",
                message="client_request_id already exists with different content",
            )

        assistant_message = session.scalar(
            select(ChatbotMessage)
            .where(
                ChatbotMessage.conversation_id == conversation_id,
                ChatbotMessage.user_id == user_id,
                ChatbotMessage.parent_message_id == existing_user_message.id,
                ChatbotMessage.role == "assistant",
            )
            .limit(1)
        )
        if assistant_message is None:
            raise ChatbotApiError(
                status_code=500,
                code="CHATBOT_CHAT_STATE_CORRUPTED",
                message="Chat state is inconsistent",
            )

        llm_run = session.scalar(
            select(ChatbotLLMRun)
            .where(
                ChatbotLLMRun.conversation_id == conversation_id,
                ChatbotLLMRun.user_id == user_id,
                ChatbotLLMRun.message_id == assistant_message.id,
            )
            .limit(1)
        )
        if llm_run is None:
            raise ChatbotApiError(
                status_code=500,
                code="CHATBOT_CHAT_STATE_CORRUPTED",
                message="Chat state is inconsistent",
            )
        return self._build_response(existing_user_message, assistant_message, llm_run, replayed=True)

    def _load_recent_messages(
        self,
        session: Session,
        *,
        user_id: str,
        conversation_id: str,
        before_sequence_number: int,
    ) -> tuple[LLMMessage, ...]:
        stmt = (
            select(ChatbotMessage)
            .where(
                ChatbotMessage.conversation_id == conversation_id,
                ChatbotMessage.user_id == user_id,
                ChatbotMessage.sequence_number < before_sequence_number,
                ChatbotMessage.status == "completed",
                ChatbotMessage.role.in_(("user", "assistant")),
            )
            .order_by(desc(ChatbotMessage.sequence_number), desc(ChatbotMessage.id))
            .limit(self.settings.chatbot_recent_message_limit)
        )
        rows = list(session.scalars(stmt))
        return tuple(LLMMessage(role=row.role, content=row.content) for row in reversed(rows))

    def _build_request(self, accepted: _AcceptedTurn, content: str) -> ChatCompletionRequest:
        builder = self._prompt_builder_factory(
            prompt_version=accepted.prompt_version,
            system_prompt=self._build_system_prompt(accepted.prompt_version),
            default_model=accepted.model,
        )
        return builder.build_request(
            request_id=accepted.client_request_id,
            model=accepted.model,
            user_message=content,
            history=accepted.history_messages,
        )

    @staticmethod
    def _build_system_prompt(prompt_version: str) -> str:
        return (
            "You are the portfolio chatbot for Pai Guangguang.\n"
            "Answer clearly, concretely, and only using the conversation context.\n"
            f"Prompt version: {prompt_version}"
        )

    def _finalize_completed(
        self,
        accepted: _AcceptedTurn,
        user_id: str,
        result: ChatCompletionResult,
        started_at: float,
    ) -> ChatCompletionData:
        with self._session() as session:
            user_message = session.get(ChatbotMessage, accepted.user_message_id)
            assistant_message = session.get(ChatbotMessage, accepted.assistant_message_id)
            llm_run = session.get(ChatbotLLMRun, accepted.llm_run_id)
            conversation = session.get(ChatbotConversation, accepted.conversation_id)
            if not all((user_message, assistant_message, llm_run, conversation)):
                raise ChatbotApiError(
                    status_code=500,
                    code="CHATBOT_CHAT_STATE_CORRUPTED",
                    message="Chat state is inconsistent",
                )

            if assistant_message.status in {"completed", "failed", "cancelled"} and llm_run.status in {"completed", "failed", "cancelled"}:
                return self._build_response(user_message, assistant_message, llm_run, replayed=True)

            now = _utcnow()
            usage = result.usage
            prompt_tokens, completion_tokens, total_tokens = self._usage_counts(usage)
            assistant_message.content = result.message.content
            assistant_message.model = result.model
            assistant_message.status = "completed"
            assistant_message.prompt_tokens = prompt_tokens
            assistant_message.completion_tokens = completion_tokens
            assistant_message.total_tokens = total_tokens
            assistant_message.error_code = None
            assistant_message.updated_at = now

            llm_run.status = "completed"
            llm_run.prompt_tokens = prompt_tokens
            llm_run.completion_tokens = completion_tokens
            llm_run.total_tokens = total_tokens
            llm_run.latency_ms = int((perf_counter() - started_at) * 1000)
            llm_run.finish_reason = result.finish_reason
            llm_run.error_code = None
            llm_run.error_message = None
            llm_run.completed_at = now
            llm_run.updated_at = now

            conversation.last_message_at = now
            conversation.updated_at = now
            session.flush()
            return self._build_response(user_message, assistant_message, llm_run, replayed=False)

    def _finalize_failed(
        self,
        accepted: _AcceptedTurn,
        user_id: str,
        exc: Exception,
        started_at: float,
    ) -> ChatCompletionData:
        with self._session() as session:
            user_message = session.get(ChatbotMessage, accepted.user_message_id)
            assistant_message = session.get(ChatbotMessage, accepted.assistant_message_id)
            llm_run = session.get(ChatbotLLMRun, accepted.llm_run_id)
            conversation = session.get(ChatbotConversation, accepted.conversation_id)
            if not all((user_message, assistant_message, llm_run, conversation)):
                raise ChatbotApiError(
                    status_code=500,
                    code="CHATBOT_CHAT_STATE_CORRUPTED",
                    message="Chat state is inconsistent",
                )

            if assistant_message.status in {"completed", "failed", "cancelled"} and llm_run.status in {"completed", "failed", "cancelled"}:
                return self._build_response(user_message, assistant_message, llm_run, replayed=True)

            now = _utcnow()
            error_code, error_message = self._error_metadata(exc)

            assistant_message.status = "failed"
            assistant_message.model = accepted.model
            assistant_message.error_code = error_code
            assistant_message.updated_at = now

            llm_run.status = "failed"
            llm_run.latency_ms = int((perf_counter() - started_at) * 1000)
            llm_run.finish_reason = None
            llm_run.error_code = error_code
            llm_run.error_message = error_message
            llm_run.completed_at = now
            llm_run.updated_at = now

            conversation.last_message_at = now
            conversation.updated_at = now
            session.flush()
            return self._build_response(user_message, assistant_message, llm_run, replayed=False)

    @staticmethod
    def _usage_counts(usage: ChatCompletionUsage | None) -> tuple[int, int, int]:
        if usage is None:
            return 0, 0, 0
        return usage.prompt_tokens, usage.completion_tokens, usage.total_tokens

    @staticmethod
    def _error_metadata(exc: Exception) -> tuple[str, str]:
        if isinstance(exc, LLMTimeoutError):
            return "CHATBOT_LLM_TIMEOUT", "LLM request timed out"
        if isinstance(exc, LLMRateLimitError):
            return "CHATBOT_LLM_RATE_LIMITED", "LLM request was rate limited"
        if isinstance(exc, LLMProtocolError):
            return "CHATBOT_LLM_PROTOCOL_ERROR", "LLM returned an invalid response"
        if isinstance(exc, LLMConfigurationError):
            return "CHATBOT_LLM_CONFIGURATION_ERROR", "LLM provider is misconfigured"
        if isinstance(exc, LLMProviderError):
            return "CHATBOT_LLM_PROVIDER_ERROR", "LLM provider request failed"
        return "CHATBOT_LLM_INTERNAL_ERROR", "LLM request failed"

    @staticmethod
    def _build_response(
        user_message: ChatbotMessage,
        assistant_message: ChatbotMessage,
        llm_run: ChatbotLLMRun,
        *,
        replayed: bool,
    ) -> ChatCompletionData:
        return ChatCompletionData(
            conversation_id=UUID(str(user_message.conversation_id)),
            client_request_id=UUID(str(user_message.client_request_id)),
            replayed=replayed,
            user_message=MessageData.model_validate(user_message),
            assistant_message=MessageData.model_validate(assistant_message),
            llm_run=ChatLLMRunData.model_validate(llm_run),
        )

    @staticmethod
    def _normalize_uuid(value: str, *, field_name: str) -> str:
        try:
            return str(UUID(str(value)))
        except Exception as exc:  # pragma: no cover - defensive
            raise ChatbotApiError(
                status_code=422,
                code="VALIDATION_ERROR",
                message=f"{field_name} must be a UUID",
            ) from exc

    def _validate_content(self, content: str) -> str:
        if not isinstance(content, str) or not content.strip():
            raise ChatbotApiError(
                status_code=422,
                code="VALIDATION_ERROR",
                message="Content cannot be empty",
            )
        if len(content) > self.settings.chatbot_message_max_chars:
            raise ChatbotApiError(
                status_code=422,
                code="CHATBOT_MESSAGE_TOO_LONG",
                message="Content is too long",
            )
        return content


_CHAT_SERVICE: ChatService | None = None


def get_chat_service() -> ChatService:
    global _CHAT_SERVICE
    if _CHAT_SERVICE is None:
        _CHAT_SERVICE = ChatService()
    return _CHAT_SERVICE
