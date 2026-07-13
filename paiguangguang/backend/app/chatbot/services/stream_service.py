from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from queue import Empty, Queue
from threading import Thread
from time import perf_counter
from typing import Iterator
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.chatbot.errors import ChatbotApiError, get_chatbot_error_spec
from app.chatbot.observability import log_chatbot_event
from app.chatbot.llm.exceptions import (
    LLMConfigurationError,
    LLMError,
    LLMProtocolError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from app.chatbot.llm.provider import ChatCompletionRequest, ChatCompletionUsage
from app.chatbot.models.conversation import ChatbotConversation
from app.chatbot.models.llm_run import ChatbotLLMRun
from app.chatbot.models.message import ChatbotMessage
from app.chatbot.schemas.chat import ChatCompletionData, ChatLLMRunData
from app.chatbot.schemas.message import MessageData
from app.chatbot.schemas.stream import (
    ChatStreamEvent,
    ChatStreamFinalStatus,
    StreamCompletedMessageData,
    StreamEndData,
    StreamErrorData,
    StreamMessageCancelledData,
    StreamMessageCompletedData,
    StreamMessageCreatedData,
    StreamMessageDeltaData,
    StreamMessageData,
    StreamMessageFailedData,
    StreamUsageUpdatedData,
    encode_chatbot_sse_keepalive,
)
from app.chatbot.services.cancellation_service import CancellationService, get_cancellation_service
from app.chatbot.services.chat_service import ChatService, _AcceptedTurn
from app.core.config import Settings, get_settings
from app.core.request_id import get_request_id


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class _TerminalState:
    content: str
    usage: ChatCompletionUsage | None
    error: StreamErrorData
    status: ChatStreamFinalStatus = "failed"
    finish_reason: str | None = None


class ChatStreamService:
    KEEPALIVE_SECONDS = 15

    def __init__(
        self,
        chat_service: ChatService | None = None,
        *,
        cancellation_service: CancellationService | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.chat_service = chat_service or ChatService(settings=self.settings)
        self._owns_chat_service = chat_service is None
        self.cancellation_service = cancellation_service or get_cancellation_service()

    def close(self) -> None:
        if self._owns_chat_service:
            self.chat_service.close()

    def stream_completion(
        self,
        user_id: str,
        conversation_id: str,
        content: str,
        client_request_id: str,
    ) -> Iterator[ChatStreamEvent | str]:
        user_id = self.chat_service._normalize_uuid(user_id, field_name="user_id")
        conversation_id = self.chat_service._normalize_uuid(conversation_id, field_name="conversation_id")
        client_request_id = self.chat_service._normalize_uuid(client_request_id, field_name="client_request_id")
        content = self.chat_service._validate_content(content)

        with self.chat_service._session() as session:
            replay = self.chat_service._load_replay(session, user_id, conversation_id, client_request_id, content)
            if replay is not None:
                if replay.assistant_message.status in {"completed", "failed", "cancelled"}:
                    return iter(self._build_replay_events(replay))
                raise ChatbotApiError(
                    status_code=409,
                    code="CHATBOT_REQUEST_IN_PROGRESS",
                    message="Request is already running",
                    details={
                        "user_message_id": str(replay.user_message.id),
                        "assistant_message_id": str(replay.assistant_message.id),
                        "llm_run_id": str(replay.llm_run.id),
                    },
                )

        self.chat_service._apply_rate_limit(user_id, conversation_id, operation="Chatbot message generation")
        lease = self.chat_service.concurrency_service.acquire(conversation_id, user_id)
        if lease is None:
            raise ChatbotApiError(
                status_code=409,
                code="CHATBOT_CONVERSATION_BUSY",
                message="Conversation is busy",
            )
        try:
            with self.chat_service._session() as session:
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
                    .order_by(ChatbotLLMRun.updated_at.desc(), ChatbotLLMRun.id.desc())
                    .limit(1)
                )
                if active_run is not None:
                    raise ChatbotApiError(
                        status_code=409,
                        code="CHATBOT_CONVERSATION_BUSY",
                        message="Conversation is busy",
                    )

                accepted = self.chat_service._accept_turn(
                    session,
                    user_id=user_id,
                    conversation=conversation,
                    content=content,
                    client_request_id=client_request_id,
                )
        finally:
            self.chat_service.concurrency_service.release(lease)

        request = self.chat_service._build_request(accepted, content)
        request_id = get_request_id()
        log_chatbot_event(
            "chatbot.stream.request.started",
            request_id=request_id,
            user_id=user_id,
            conversation_id=accepted.conversation_id,
            message_id=accepted.assistant_message_id,
            llm_run_id=accepted.llm_run_id,
            provider="deepseek",
            model=accepted.model,
            status="pending",
            content=content,
        )
        queue: Queue[ChatStreamEvent | None] = Queue()
        producer = Thread(
            target=self._produce_stream_events,
            args=(queue, accepted, user_id, request, request_id),
            daemon=True,
        )
        producer.start()

        def event_stream() -> Iterator[ChatStreamEvent | str]:
            stream_end_sent = False
            disconnected = False
            yield ChatStreamEvent(
                event="message.created",
                data=self._build_created_data(accepted, content=content, replayed=False),
                sequence=1,
            )
            try:
                while True:
                    try:
                        event = queue.get(timeout=self.KEEPALIVE_SECONDS)
                    except Empty:
                        if not producer.is_alive():
                            break
                        yield encode_chatbot_sse_keepalive()
                        continue
                    if event is None:
                        break
                    if isinstance(event, ChatStreamEvent) and event.event == "stream.end":
                        stream_end_sent = True
                    yield event
            except GeneratorExit:
                disconnected = True
                raise
            finally:
                if not stream_end_sent and not disconnected:
                    disconnected = True
                if disconnected and not stream_end_sent:
                    log_chatbot_event(
                        "chatbot.stream.client_disconnected",
                        request_id=request_id,
                        user_id=user_id,
                        conversation_id=accepted.conversation_id,
                        message_id=accepted.assistant_message_id,
                        llm_run_id=accepted.llm_run_id,
                        provider="deepseek",
                        model=accepted.model,
                        status="disconnected",
                    )

        return event_stream()

    def stream_retry(
        self,
        user_id: str,
        conversation_id: str,
        assistant_message_id: str,
        client_request_id: str,
    ) -> Iterator[ChatStreamEvent | str]:
        return self._stream_variant_turn(
            user_id=user_id,
            conversation_id=conversation_id,
            assistant_message_id=assistant_message_id,
            client_request_id=client_request_id,
            require_latest_turn=False,
        )

    def stream_regenerate(
        self,
        user_id: str,
        conversation_id: str,
        assistant_message_id: str,
        client_request_id: str,
    ) -> Iterator[ChatStreamEvent | str]:
        return self._stream_variant_turn(
            user_id=user_id,
            conversation_id=conversation_id,
            assistant_message_id=assistant_message_id,
            client_request_id=client_request_id,
            require_latest_turn=True,
        )

    def _stream_variant_turn(
        self,
        *,
        user_id: str,
        conversation_id: str,
        assistant_message_id: str,
        client_request_id: str,
        require_latest_turn: bool,
    ) -> Iterator[ChatStreamEvent | str]:
        user_id = self.chat_service._normalize_uuid(user_id, field_name="user_id")
        conversation_id = self.chat_service._normalize_uuid(conversation_id, field_name="conversation_id")
        assistant_message_id = self.chat_service._normalize_uuid(assistant_message_id, field_name="assistant_message_id")
        client_request_id = self.chat_service._normalize_uuid(client_request_id, field_name="client_request_id")

        self.chat_service._apply_rate_limit(user_id, conversation_id, operation="Chatbot message regeneration")
        lease = self.chat_service.concurrency_service.acquire(conversation_id, user_id)
        if lease is None:
            raise ChatbotApiError(
                status_code=409,
                code="CHATBOT_CONVERSATION_BUSY",
                message="Conversation is busy",
            )
        try:
            with self.chat_service._session() as session:
                assistant_message, parent_user_message, llm_run = self._load_variant_replay(
                    session,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    assistant_message_id=assistant_message_id,
                    client_request_id=client_request_id,
                )
                if assistant_message is not None and parent_user_message is not None and llm_run is not None:
                    if llm_run.status in {"pending", "streaming"}:
                        raise ChatbotApiError(
                            status_code=409,
                            code="CHATBOT_REQUEST_IN_PROGRESS",
                            message="Request is already running",
                            details={
                                "assistant_message_id": str(assistant_message.id),
                                "llm_run_id": str(llm_run.id),
                            },
                        )
                    replay = ChatCompletionData(
                        conversation_id=UUID(str(parent_user_message.conversation_id)),
                        client_request_id=UUID(str(client_request_id)),
                        replayed=True,
                        user_message=MessageData.model_validate(parent_user_message),
                        assistant_message=MessageData.model_validate(assistant_message),
                        llm_run=ChatLLMRunData.model_validate(llm_run),
                    )
                    if assistant_message.status in {"completed", "failed", "cancelled"}:
                        return iter(self._build_replay_events(replay))
                    raise ChatbotApiError(
                        status_code=409,
                        code="CHATBOT_MESSAGE_NOT_RETRYABLE",
                        message="Message is not retryable",
                    )

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
                    .order_by(ChatbotLLMRun.updated_at.desc(), ChatbotLLMRun.id.desc())
                    .limit(1)
                )
                if active_run is not None:
                    raise ChatbotApiError(
                        status_code=409,
                        code="CHATBOT_CONVERSATION_BUSY",
                        message="Conversation is busy",
                    )

                parent_user_message = session.get(ChatbotMessage, assistant_message_id)
                if (
                    parent_user_message is None
                    or parent_user_message.user_id != user_id
                    or parent_user_message.conversation_id != conversation_id
                ):
                    raise ChatbotApiError(
                        status_code=404,
                        code="CHATBOT_MESSAGE_NOT_FOUND",
                        message="Message not found",
                    )
                if parent_user_message.role != "assistant" and parent_user_message.role != "user":
                    raise ChatbotApiError(
                        status_code=404,
                        code="CHATBOT_MESSAGE_NOT_FOUND",
                        message="Message not found",
                    )
                if parent_user_message.role != "assistant":
                    raise ChatbotApiError(
                        status_code=409,
                        code="CHATBOT_MESSAGE_NOT_RETRYABLE",
                        message="Message is not retryable",
                    )
                if parent_user_message.parent_message_id is None:
                    raise ChatbotApiError(
                        status_code=409,
                        code="CHATBOT_MESSAGE_NOT_RETRYABLE",
                        message="Message is not retryable",
                    )
                if require_latest_turn and parent_user_message.status not in {"completed", "failed", "cancelled"}:
                    raise ChatbotApiError(
                        status_code=409,
                        code="CHATBOT_MESSAGE_NOT_RETRYABLE",
                        message="Message is not retryable",
                    )
                if not require_latest_turn and parent_user_message.status not in {"failed", "cancelled"}:
                    raise ChatbotApiError(
                        status_code=409,
                        code="CHATBOT_MESSAGE_NOT_RETRYABLE",
                        message="Message is not retryable",
                    )

                base_user_message = session.get(ChatbotMessage, parent_user_message.parent_message_id)
                if base_user_message is None or base_user_message.user_id != user_id:
                    raise ChatbotApiError(
                        status_code=500,
                        code="CHATBOT_CHAT_STATE_CORRUPTED",
                        message="Chat state is inconsistent",
                    )

                if require_latest_turn:
                    later_user_message = session.scalar(
                        select(ChatbotMessage)
                        .where(
                            ChatbotMessage.conversation_id == conversation_id,
                            ChatbotMessage.user_id == user_id,
                            ChatbotMessage.role == "user",
                            ChatbotMessage.sequence_number > base_user_message.sequence_number,
                        )
                        .limit(1)
                    )
                    if later_user_message is not None:
                        raise ChatbotApiError(
                            status_code=409,
                            code="CHATBOT_REGENERATE_NOT_LATEST_TURN",
                            message="Regenerate requires the latest user turn",
                        )

                accepted = self.chat_service._accept_variant_turn(
                    session,
                    user_id=user_id,
                    conversation=conversation,
                    parent_user_message=base_user_message,
                    client_request_id=client_request_id,
                )
        finally:
            self.chat_service.concurrency_service.release(lease)

        request = self.chat_service._build_request(accepted, base_user_message.content)
        request_id = get_request_id()
        log_chatbot_event(
            "chatbot.stream.request.started",
            request_id=request_id,
            user_id=user_id,
            conversation_id=accepted.conversation_id,
            message_id=accepted.assistant_message_id,
            llm_run_id=accepted.llm_run_id,
            provider="deepseek",
            model=accepted.model,
            status="pending",
            content=base_user_message.content,
        )
        queue: Queue[ChatStreamEvent | None] = Queue()
        producer = Thread(
            target=self._produce_stream_events,
            args=(queue, accepted, user_id, request, request_id),
            daemon=True,
        )
        producer.start()

        def event_stream() -> Iterator[ChatStreamEvent | str]:
            stream_end_sent = False
            disconnected = False
            yield ChatStreamEvent(
                event="message.created",
                data=self._build_created_data(accepted, content=base_user_message.content, replayed=False),
                sequence=1,
            )
            try:
                while True:
                    try:
                        event = queue.get(timeout=self.KEEPALIVE_SECONDS)
                    except Empty:
                        if not producer.is_alive():
                            break
                        yield encode_chatbot_sse_keepalive()
                        continue
                    if event is None:
                        break
                    if isinstance(event, ChatStreamEvent) and event.event == "stream.end":
                        stream_end_sent = True
                    yield event
            except GeneratorExit:
                disconnected = True
                raise
            finally:
                if not stream_end_sent and not disconnected:
                    disconnected = True
                if disconnected and not stream_end_sent:
                    log_chatbot_event(
                        "chatbot.stream.client_disconnected",
                        request_id=request_id,
                        user_id=user_id,
                        conversation_id=accepted.conversation_id,
                        message_id=accepted.assistant_message_id,
                        llm_run_id=accepted.llm_run_id,
                        provider="deepseek",
                        model=accepted.model,
                        status="disconnected",
                    )

        return event_stream()

    def _load_variant_replay(
        self,
        session: Session,
        *,
        user_id: str,
        conversation_id: str,
        assistant_message_id: str,
        client_request_id: str,
    ) -> tuple[ChatbotMessage | None, ChatbotMessage | None, ChatbotLLMRun | None]:
        llm_run = session.scalar(
            select(ChatbotLLMRun)
            .where(
                ChatbotLLMRun.user_id == user_id,
                ChatbotLLMRun.conversation_id == conversation_id,
                ChatbotLLMRun.request_id == client_request_id,
            )
            .limit(1)
        )
        if llm_run is None:
            return None, None, None

        assistant_message = session.get(ChatbotMessage, llm_run.message_id)
        if assistant_message is None or assistant_message.parent_message_id is None:
            raise ChatbotApiError(
                status_code=500,
                code="CHATBOT_CHAT_STATE_CORRUPTED",
                message="Chat state is inconsistent",
            )

        user_message = session.get(ChatbotMessage, assistant_message.parent_message_id)
        if user_message is None:
            raise ChatbotApiError(
                status_code=500,
                code="CHATBOT_CHAT_STATE_CORRUPTED",
                message="Chat state is inconsistent",
            )
        if user_message.user_id != user_id or user_message.conversation_id != conversation_id:
            raise ChatbotApiError(
                status_code=404,
                code="CHATBOT_MESSAGE_NOT_FOUND",
                message="Message not found",
            )
        return assistant_message, user_message, llm_run

    def _produce_stream_events(
        self,
        queue: Queue[ChatStreamEvent | None],
        accepted: _AcceptedTurn,
        user_id: str,
        request: ChatCompletionRequest,
        request_id: str | None = None,
    ) -> None:
        request_id = request_id or get_request_id()
        started_at = perf_counter()
        next_sequence = 2
        partial_content = ""
        usage: ChatCompletionUsage | None = None
        first_delta_at: float | None = None
        try:
            for llm_event in self.chat_service.llm_client.stream(request):
                if self.cancellation_service.is_requested(accepted.conversation_id, accepted.assistant_message_id):
                    if not self._finalize_cancelled(
                        accepted,
                        user_id,
                        content=partial_content,
                        usage=usage,
                        started_at=started_at,
                        first_delta_at=first_delta_at,
                        request_id=request_id,
                    ):
                        continue
                    self._refresh_short_term_memory(user_id, accepted.conversation_id)
                    queue.put(
                        ChatStreamEvent(
                            event="message.cancelled",
                            data=self._build_cancelled_data(
                                accepted,
                                sequence=next_sequence,
                                content=partial_content,
                            ),
                            sequence=next_sequence,
                        )
                    )
                    next_sequence += 1
                    queue.put(
                        ChatStreamEvent(
                            event="usage.updated",
                            data=self._build_usage_data(
                                accepted,
                                sequence=next_sequence,
                                usage=usage,
                            ),
                            sequence=next_sequence,
                        )
                    )
                    next_sequence += 1
                    queue.put(
                        ChatStreamEvent(
                            event="stream.end",
                            data=self._build_end_data(
                                accepted,
                                sequence=next_sequence,
                                final_status="cancelled",
                            ),
                            sequence=next_sequence,
                        )
                    )
                    return
                if llm_event.kind == "delta":
                    delta = llm_event.content or ""
                    if not delta:
                        continue
                    partial_content += delta
                    if first_delta_at is None:
                        first_delta_at = perf_counter()
                        log_chatbot_event(
                            "chatbot.stream.first_token",
                            request_id=request_id,
                            user_id=user_id,
                            conversation_id=accepted.conversation_id,
                            message_id=accepted.assistant_message_id,
                            llm_run_id=accepted.llm_run_id,
                            provider="deepseek",
                            model=accepted.model,
                            status="streaming",
                            latency_ms=int((first_delta_at - started_at) * 1000),
                            content_length=len(partial_content),
                        )
                    self._checkpoint_partial(
                        accepted,
                        user_id,
                        partial_content=partial_content,
                        usage=usage,
                        started_at=started_at,
                        first_delta_at=first_delta_at,
                    )
                    queue.put(
                        ChatStreamEvent(
                            event="message.delta",
                            data=self._build_delta_data(
                                accepted,
                                sequence=next_sequence,
                                delta=delta,
                                content_length=len(partial_content),
                            ),
                            sequence=next_sequence,
                        )
                    )
                    next_sequence += 1
                    continue

                if llm_event.kind == "usage":
                    usage = llm_event.usage
                    self._checkpoint_partial(
                        accepted,
                        user_id,
                        partial_content=partial_content,
                        usage=usage,
                        started_at=started_at,
                        first_delta_at=first_delta_at,
                    )
                    continue

                if llm_event.kind == "completed":
                    final_content = llm_event.content if llm_event.content is not None else partial_content
                    usage = llm_event.usage or usage
                    self._finalize_completed(
                        accepted,
                        user_id,
                        content=final_content,
                        usage=usage,
                        finish_reason=llm_event.finish_reason,
                        started_at=started_at,
                        first_delta_at=first_delta_at,
                        request_id=request_id,
                    )
                    self._refresh_short_term_memory(user_id, accepted.conversation_id)
                    queue.put(
                        ChatStreamEvent(
                            event="message.completed",
                            data=self._build_completed_data(
                                accepted,
                                sequence=next_sequence,
                                content=final_content,
                                finish_reason=llm_event.finish_reason,
                            ),
                            sequence=next_sequence,
                        )
                    )
                    next_sequence += 1
                    queue.put(
                        ChatStreamEvent(
                            event="usage.updated",
                            data=self._build_usage_data(
                                accepted,
                                sequence=next_sequence,
                                usage=usage,
                            ),
                            sequence=next_sequence,
                        )
                    )
                    next_sequence += 1
                    queue.put(
                        ChatStreamEvent(
                            event="stream.end",
                            data=self._build_end_data(
                                accepted,
                                sequence=next_sequence,
                                final_status="completed",
                            ),
                            sequence=next_sequence,
                        )
                    )
                    return

                if llm_event.kind == "cancelled":
                    self._finalize_cancelled(
                        accepted,
                        user_id,
                        content=partial_content,
                        usage=usage,
                        started_at=started_at,
                        first_delta_at=first_delta_at,
                        request_id=request_id,
                    )
                    self._refresh_short_term_memory(user_id, accepted.conversation_id)
                    queue.put(
                        ChatStreamEvent(
                            event="message.cancelled",
                            data=self._build_cancelled_data(
                                accepted,
                                sequence=next_sequence,
                                content=partial_content,
                            ),
                            sequence=next_sequence,
                        )
                    )
                    next_sequence += 1
                    queue.put(
                        ChatStreamEvent(
                            event="usage.updated",
                            data=self._build_usage_data(
                                accepted,
                                sequence=next_sequence,
                                usage=usage,
                            ),
                            sequence=next_sequence,
                        )
                    )
                    next_sequence += 1
                    queue.put(
                        ChatStreamEvent(
                            event="stream.end",
                            data=self._build_end_data(
                                accepted,
                                sequence=next_sequence,
                                final_status="cancelled",
                            ),
                            sequence=next_sequence,
                        )
                    )
                    return

            raise LLMProtocolError("Stream ended without a terminal event")
        except Exception as exc:
            terminal_state = self._terminal_state_from_exception(exc, content=partial_content, usage=usage)
            self._finalize_failed(
                accepted,
                user_id,
                terminal_state=terminal_state,
                started_at=started_at,
                first_delta_at=first_delta_at,
                request_id=request_id,
            )
            self._refresh_short_term_memory(user_id, accepted.conversation_id)
            queue.put(
                ChatStreamEvent(
                    event="message.failed",
                    data=self._build_failed_data(
                        accepted,
                        sequence=next_sequence,
                        terminal_state=terminal_state,
                    ),
                    sequence=next_sequence,
                )
            )
            next_sequence += 1
            queue.put(
                ChatStreamEvent(
                    event="usage.updated",
                    data=self._build_usage_data(
                        accepted,
                        sequence=next_sequence,
                        usage=terminal_state.usage,
                    ),
                    sequence=next_sequence,
                )
            )
            next_sequence += 1
            queue.put(
                ChatStreamEvent(
                    event="stream.end",
                    data=self._build_end_data(
                        accepted,
                        sequence=next_sequence,
                        final_status="failed",
                    ),
                    sequence=next_sequence,
                )
            )
        finally:
            queue.put(None)

    def _checkpoint_partial(
        self,
        accepted: _AcceptedTurn,
        user_id: str,
        *,
        partial_content: str,
        usage: ChatCompletionUsage | None,
        started_at: float,
        first_delta_at: float | None,
    ) -> None:
        with self.chat_service._session() as session:
            user_message, assistant_message, llm_run, conversation = self._load_owned_turn(session, accepted, user_id)
            now = _utcnow()
            if assistant_message.status == "pending":
                assistant_message.status = "streaming"
            assistant_message.content = partial_content
            assistant_message.model = accepted.model
            assistant_message.updated_at = now

            if llm_run.status == "pending":
                llm_run.status = "streaming"
                llm_run.started_at = accepted.created_at
                if first_delta_at is not None:
                    llm_run.first_token_latency_ms = int((first_delta_at - started_at) * 1000)
            llm_run.updated_at = now

            if usage is not None:
                prompt_tokens, completion_tokens, total_tokens = self._usage_counts(usage)
                assistant_message.prompt_tokens = prompt_tokens
                assistant_message.completion_tokens = completion_tokens
                assistant_message.total_tokens = total_tokens
                llm_run.prompt_tokens = prompt_tokens
                llm_run.completion_tokens = completion_tokens
                llm_run.total_tokens = total_tokens

            conversation.updated_at = now
            session.flush()

    def _finalize_completed(
        self,
        accepted: _AcceptedTurn,
        user_id: str,
        *,
        content: str,
        usage: ChatCompletionUsage | None,
        finish_reason: str | None,
        started_at: float,
        first_delta_at: float | None,
        request_id: str,
    ) -> None:
        with self.chat_service._session() as session:
            user_message, assistant_message, llm_run, conversation = self._load_owned_turn(session, accepted, user_id)
            now = _utcnow()
            prompt_tokens, completion_tokens, total_tokens = self._usage_counts(usage)
            assistant_message.content = content
            assistant_message.model = accepted.model
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
            if first_delta_at is not None:
                llm_run.first_token_latency_ms = int((first_delta_at - started_at) * 1000)
            llm_run.finish_reason = finish_reason
            llm_run.error_code = None
            llm_run.error_message = None
            llm_run.completed_at = now
            llm_run.updated_at = now

            conversation.last_message_at = now
            conversation.updated_at = now
            session.flush()
            log_chatbot_event(
                "chatbot.stream.completed",
                request_id=request_id,
                user_id=user_id,
                conversation_id=str(conversation.id),
                message_id=assistant_message.id,
                llm_run_id=llm_run.id,
                provider=llm_run.provider,
                model=assistant_message.model or llm_run.model,
                status="completed",
                latency_ms=llm_run.latency_ms,
                first_token_latency_ms=llm_run.first_token_latency_ms,
                prompt_tokens=llm_run.prompt_tokens,
                completion_tokens=llm_run.completion_tokens,
                total_tokens=llm_run.total_tokens,
                content=assistant_message.content,
            )

    def _finalize_cancelled(
        self,
        accepted: _AcceptedTurn,
        user_id: str,
        *,
        content: str,
        usage: ChatCompletionUsage | None,
        started_at: float,
        first_delta_at: float | None,
        request_id: str,
    ) -> bool:
        with self.chat_service._session() as session:
            user_message, assistant_message, llm_run, conversation = self._load_owned_turn(session, accepted, user_id)
            if assistant_message.status in {"completed", "failed", "cancelled"} and llm_run.status in {
                "completed",
                "failed",
                "cancelled",
            }:
                return False
            now = _utcnow()
            prompt_tokens, completion_tokens, total_tokens = self._usage_counts(usage)
            assistant_message.content = content
            assistant_message.model = accepted.model
            assistant_message.status = "cancelled"
            assistant_message.prompt_tokens = prompt_tokens
            assistant_message.completion_tokens = completion_tokens
            assistant_message.total_tokens = total_tokens
            assistant_message.error_code = None
            assistant_message.updated_at = now

            llm_run.status = "cancelled"
            llm_run.prompt_tokens = prompt_tokens
            llm_run.completion_tokens = completion_tokens
            llm_run.total_tokens = total_tokens
            llm_run.latency_ms = int((perf_counter() - started_at) * 1000)
            if first_delta_at is not None:
                llm_run.first_token_latency_ms = int((first_delta_at - started_at) * 1000)
            llm_run.finish_reason = "cancelled"
            llm_run.error_code = None
            llm_run.error_message = None
            llm_run.completed_at = now
            llm_run.updated_at = now

            conversation.last_message_at = now
            conversation.updated_at = now
            session.flush()
            log_chatbot_event(
                "chatbot.stream.cancelled",
                request_id=request_id,
                user_id=user_id,
                conversation_id=str(conversation.id),
                message_id=assistant_message.id,
                llm_run_id=llm_run.id,
                provider=llm_run.provider,
                model=assistant_message.model or llm_run.model,
                status="cancelled",
                latency_ms=llm_run.latency_ms,
                first_token_latency_ms=llm_run.first_token_latency_ms,
                prompt_tokens=llm_run.prompt_tokens,
                completion_tokens=llm_run.completion_tokens,
                total_tokens=llm_run.total_tokens,
                content=assistant_message.content,
            )
        return True

    def _finalize_failed(
        self,
        accepted: _AcceptedTurn,
        user_id: str,
        *,
        terminal_state: _TerminalState,
        started_at: float,
        first_delta_at: float | None,
        request_id: str,
    ) -> None:
        with self.chat_service._session() as session:
            user_message, assistant_message, llm_run, conversation = self._load_owned_turn(session, accepted, user_id)
            if assistant_message.status in {"completed", "failed", "cancelled"} and llm_run.status in {
                "completed",
                "failed",
                "cancelled",
            }:
                return
            now = _utcnow()
            prompt_tokens, completion_tokens, total_tokens = self._usage_counts(terminal_state.usage)
            assistant_message.content = terminal_state.content
            assistant_message.model = accepted.model
            assistant_message.status = "failed"
            assistant_message.prompt_tokens = prompt_tokens
            assistant_message.completion_tokens = completion_tokens
            assistant_message.total_tokens = total_tokens
            assistant_message.error_code = terminal_state.error.code
            assistant_message.updated_at = now

            llm_run.status = "failed"
            llm_run.prompt_tokens = prompt_tokens
            llm_run.completion_tokens = completion_tokens
            llm_run.total_tokens = total_tokens
            llm_run.latency_ms = int((perf_counter() - started_at) * 1000)
            if first_delta_at is not None:
                llm_run.first_token_latency_ms = int((first_delta_at - started_at) * 1000)
            llm_run.finish_reason = None
            llm_run.error_code = terminal_state.error.code
            llm_run.error_message = terminal_state.error.message
            llm_run.completed_at = now
            llm_run.updated_at = now

            conversation.last_message_at = now
            conversation.updated_at = now
            session.flush()
            log_chatbot_event(
                "chatbot.stream.failed",
                request_id=request_id,
                user_id=user_id,
                conversation_id=str(conversation.id),
                message_id=assistant_message.id,
                llm_run_id=llm_run.id,
                provider=llm_run.provider,
                model=assistant_message.model or llm_run.model,
                status="failed",
                error_code=terminal_state.error.code,
                latency_ms=llm_run.latency_ms,
                first_token_latency_ms=llm_run.first_token_latency_ms,
                prompt_tokens=llm_run.prompt_tokens,
                completion_tokens=llm_run.completion_tokens,
                total_tokens=llm_run.total_tokens,
                content=assistant_message.content,
                reason=type(terminal_state.error).__name__,
            )

    def _load_owned_turn(
        self,
        session: Session,
        accepted: _AcceptedTurn,
        user_id: str,
    ) -> tuple[ChatbotMessage, ChatbotMessage, ChatbotLLMRun, ChatbotConversation]:
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
        if (
            user_message.user_id != user_id
            or assistant_message.user_id != user_id
            or llm_run.user_id != user_id
            or conversation.user_id != user_id
        ):
            raise ChatbotApiError(
                status_code=404,
                code="CHATBOT_CONVERSATION_NOT_FOUND",
                message="Conversation not found",
            )
        return user_message, assistant_message, llm_run, conversation

    def _build_replay_events(self, replay: ChatCompletionData) -> list[ChatStreamEvent]:
        events: list[ChatStreamEvent] = [
            ChatStreamEvent(
                event="message.created",
                data=self._build_created_data_from_replay(replay, replayed=True),
                sequence=1,
            )
        ]
        next_sequence = 2
        assistant_message = replay.assistant_message
        llm_run = replay.llm_run

        if assistant_message.status == "completed":
            events.append(
                ChatStreamEvent(
                    event="message.completed",
                    data=StreamMessageCompletedData(
                        schema_version="1",
                        request_id=replay.client_request_id,
                        conversation_id=replay.conversation_id,
                        assistant_message_id=assistant_message.id,
                        sequence=next_sequence,
                        created_at=assistant_message.updated_at,
                        message=StreamCompletedMessageData(
                            id=assistant_message.id,
                            content=assistant_message.content,
                            sequence_number=assistant_message.sequence_number,
                            model=assistant_message.model,
                            updated_at=assistant_message.updated_at,
                        ),
                        finish_reason=llm_run.finish_reason,
                    ),
                    sequence=next_sequence,
                )
            )
        elif assistant_message.status == "cancelled":
            events.append(
                ChatStreamEvent(
                    event="message.cancelled",
                    data=self._build_cancelled_data(
                        replay,
                        sequence=next_sequence,
                        content=assistant_message.content,
                    ),
                    sequence=next_sequence,
                )
            )
        else:
            events.append(
                ChatStreamEvent(
                    event="message.failed",
                    data=self._build_failed_data_from_replay(replay, sequence=next_sequence),
                    sequence=next_sequence,
                )
            )

        next_sequence += 1
        events.append(
            ChatStreamEvent(
                event="usage.updated",
                data=self._build_usage_data_from_run(replay, sequence=next_sequence),
                sequence=next_sequence,
            )
        )
        next_sequence += 1
        events.append(
            ChatStreamEvent(
                event="stream.end",
                data=StreamEndData(
                    schema_version="1",
                    request_id=replay.client_request_id,
                    conversation_id=replay.conversation_id,
                    assistant_message_id=assistant_message.id,
                    sequence=next_sequence,
                    created_at=assistant_message.updated_at,
                    final_status=assistant_message.status,  # type: ignore[arg-type]
                ),
                sequence=next_sequence,
            )
        )
        return events

    def _build_created_data(
        self,
        accepted: _AcceptedTurn,
        *,
        content: str,
        replayed: bool,
    ) -> StreamMessageCreatedData:
        return StreamMessageCreatedData(
            schema_version="1",
            request_id=UUID(str(accepted.client_request_id)),
            conversation_id=UUID(str(accepted.conversation_id)),
            assistant_message_id=UUID(str(accepted.assistant_message_id)),
            sequence=1,
            created_at=accepted.created_at,
            replayed=replayed,
            user_message=StreamMessageData(
                id=UUID(str(accepted.user_message_id)),
                sequence_number=accepted.user_sequence,
                status="completed",
                content=content,
                model=None,
                updated_at=accepted.created_at,
            ),
            assistant_message=StreamMessageData(
                id=UUID(str(accepted.assistant_message_id)),
                sequence_number=accepted.assistant_sequence,
                status="pending",
                content="",
                model=accepted.model,
                updated_at=accepted.created_at,
            ),
        )

    def _build_created_data_from_replay(self, replay: ChatCompletionData, *, replayed: bool) -> StreamMessageCreatedData:
        user_message = replay.user_message
        assistant_message = replay.assistant_message
        return StreamMessageCreatedData(
            schema_version="1",
            request_id=replay.client_request_id,
            conversation_id=replay.conversation_id,
            assistant_message_id=assistant_message.id,
            sequence=1,
            created_at=assistant_message.created_at,
            replayed=replayed,
            user_message=StreamMessageData(
                id=user_message.id,
                sequence_number=user_message.sequence_number,
                status=user_message.status,
                content=user_message.content,
                model=user_message.model,
                updated_at=user_message.updated_at,
            ),
            assistant_message=StreamMessageData(
                id=assistant_message.id,
                sequence_number=assistant_message.sequence_number,
                status=assistant_message.status,
                content=assistant_message.content,
                model=assistant_message.model,
                updated_at=assistant_message.updated_at,
            ),
        )

    def _build_delta_data(
        self,
        accepted: _AcceptedTurn,
        *,
        sequence: int,
        delta: str,
        content_length: int,
    ) -> StreamMessageDeltaData:
        return StreamMessageDeltaData(
            schema_version="1",
            request_id=UUID(str(accepted.client_request_id)),
            conversation_id=UUID(str(accepted.conversation_id)),
            assistant_message_id=UUID(str(accepted.assistant_message_id)),
            sequence=sequence,
            created_at=_utcnow(),
            delta=delta,
            content_length=content_length,
        )

    def _build_completed_data(
        self,
        accepted: _AcceptedTurn,
        *,
        sequence: int,
        content: str,
        finish_reason: str | None,
    ) -> StreamMessageCompletedData:
        return StreamMessageCompletedData(
            schema_version="1",
            request_id=UUID(str(accepted.client_request_id)),
            conversation_id=UUID(str(accepted.conversation_id)),
            assistant_message_id=UUID(str(accepted.assistant_message_id)),
            sequence=sequence,
            created_at=_utcnow(),
            message=StreamCompletedMessageData(
                id=UUID(str(accepted.assistant_message_id)),
                content=content,
                sequence_number=accepted.assistant_sequence,
                model=accepted.model,
                updated_at=_utcnow(),
            ),
            finish_reason=finish_reason,
        )

    def _build_cancelled_data(
        self,
        replay_or_accepted: ChatCompletionData | _AcceptedTurn,
        *,
        sequence: int,
        content: str,
    ) -> StreamMessageCancelledData:
        if isinstance(replay_or_accepted, ChatCompletionData):
            request_id = replay_or_accepted.client_request_id
            conversation_id = replay_or_accepted.conversation_id
            assistant_message_id = replay_or_accepted.assistant_message.id
            created_at = replay_or_accepted.assistant_message.updated_at
        else:
            request_id = UUID(str(replay_or_accepted.client_request_id))
            conversation_id = UUID(str(replay_or_accepted.conversation_id))
            assistant_message_id = UUID(str(replay_or_accepted.assistant_message_id))
            created_at = replay_or_accepted.created_at
        return StreamMessageCancelledData(
            schema_version="1",
            request_id=request_id,
            conversation_id=conversation_id,
            assistant_message_id=assistant_message_id,
            sequence=sequence,
            created_at=created_at,
            content=content,
        )

    def _build_failed_data(
        self,
        accepted: _AcceptedTurn,
        *,
        sequence: int,
        terminal_state: _TerminalState,
    ) -> StreamMessageFailedData:
        return StreamMessageFailedData(
            schema_version="1",
            request_id=UUID(str(accepted.client_request_id)),
            conversation_id=UUID(str(accepted.conversation_id)),
            assistant_message_id=UUID(str(accepted.assistant_message_id)),
            sequence=sequence,
            created_at=_utcnow(),
            error=terminal_state.error,
            partial=bool(terminal_state.content),
            content=terminal_state.content,
        )

    def _build_failed_data_from_replay(self, replay: ChatCompletionData, *, sequence: int) -> StreamMessageFailedData:
        assistant_message = replay.assistant_message
        llm_run = replay.llm_run
        return StreamMessageFailedData(
            schema_version="1",
            request_id=replay.client_request_id,
            conversation_id=replay.conversation_id,
            assistant_message_id=assistant_message.id,
            sequence=sequence,
            created_at=assistant_message.updated_at,
            error=StreamErrorData(
                code=llm_run.error_code or assistant_message.error_code or "CHATBOT_STREAM_ERROR",
                message=llm_run.error_message or "Generation failed",
                retryable=get_chatbot_error_spec(
                    llm_run.error_code or assistant_message.error_code or "CHATBOT_STREAM_ERROR"
                ).retryable,
            ),
            partial=bool(assistant_message.content),
            content=assistant_message.content,
        )

    def _build_usage_data(
        self,
        accepted: _AcceptedTurn,
        *,
        sequence: int,
        usage: ChatCompletionUsage | None,
    ) -> StreamUsageUpdatedData:
        if usage is None:
            return StreamUsageUpdatedData(
                schema_version="1",
                request_id=UUID(str(accepted.client_request_id)),
                conversation_id=UUID(str(accepted.conversation_id)),
                assistant_message_id=UUID(str(accepted.assistant_message_id)),
                sequence=sequence,
                created_at=_utcnow(),
                prompt_tokens=None,
                completion_tokens=None,
                total_tokens=None,
                source="unknown",
            )
        prompt_tokens, completion_tokens, total_tokens = self._usage_counts(usage)
        return StreamUsageUpdatedData(
            schema_version="1",
            request_id=UUID(str(accepted.client_request_id)),
            conversation_id=UUID(str(accepted.conversation_id)),
            assistant_message_id=UUID(str(accepted.assistant_message_id)),
            sequence=sequence,
            created_at=_utcnow(),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            source="provider",
        )

    def _build_usage_data_from_run(self, replay: ChatCompletionData, *, sequence: int) -> StreamUsageUpdatedData:
        llm_run = replay.llm_run
        has_usage = any((llm_run.prompt_tokens, llm_run.completion_tokens, llm_run.total_tokens))
        return StreamUsageUpdatedData(
            schema_version="1",
            request_id=replay.client_request_id,
            conversation_id=replay.conversation_id,
            assistant_message_id=replay.assistant_message.id,
            sequence=sequence,
            created_at=replay.assistant_message.updated_at,
            prompt_tokens=llm_run.prompt_tokens if has_usage else None,
            completion_tokens=llm_run.completion_tokens if has_usage else None,
            total_tokens=llm_run.total_tokens if has_usage else None,
            source="provider" if has_usage else "unknown",
        )

    def _build_end_data(
        self,
        accepted: _AcceptedTurn,
        *,
        sequence: int,
        final_status: ChatStreamFinalStatus,
    ) -> StreamEndData:
        return StreamEndData(
            schema_version="1",
            request_id=UUID(str(accepted.client_request_id)),
            conversation_id=UUID(str(accepted.conversation_id)),
            assistant_message_id=UUID(str(accepted.assistant_message_id)),
            sequence=sequence,
            created_at=_utcnow(),
            final_status=final_status,
        )

    @staticmethod
    def _usage_counts(usage: ChatCompletionUsage | None) -> tuple[int, int, int]:
        if usage is None:
            return 0, 0, 0
        return usage.prompt_tokens, usage.completion_tokens, usage.total_tokens

    def _terminal_state_from_exception(
        self,
        exc: Exception,
        *,
        content: str,
        usage: ChatCompletionUsage | None,
    ) -> _TerminalState:
        if isinstance(exc, LLMTimeoutError):
            return _TerminalState(
                content=content,
                usage=usage,
                error=StreamErrorData(
                    code="CHATBOT_LLM_TIMEOUT",
                    message="Generation timed out",
                    retryable=True,
                ),
            )
        if isinstance(exc, LLMRateLimitError):
            return _TerminalState(
                content=content,
                usage=usage,
                error=StreamErrorData(
                    code="CHATBOT_LLM_RATE_LIMITED",
                    message="Generation was rate limited",
                    retryable=True,
                ),
            )
        if isinstance(exc, LLMProviderError):
            return _TerminalState(
                content=content,
                usage=usage,
                error=StreamErrorData(
                    code="CHATBOT_LLM_PROVIDER_ERROR",
                    message="Generation failed",
                    retryable=exc.retryable,
                ),
            )
        if isinstance(exc, LLMConfigurationError):
            return _TerminalState(
                content=content,
                usage=usage,
                error=StreamErrorData(
                    code="CHATBOT_LLM_CONFIGURATION_ERROR",
                    message="LLM provider is misconfigured",
                    retryable=False,
                ),
            )
        if isinstance(exc, LLMProtocolError):
            return _TerminalState(
                content=content,
                usage=usage,
                error=StreamErrorData(
                    code="CHATBOT_STREAM_ERROR",
                    message="Internal stream processing failed",
                    retryable=True,
                ),
            )
        if isinstance(exc, LLMError):
            return _TerminalState(
                content=content,
                usage=usage,
                error=StreamErrorData(
                    code="CHATBOT_STREAM_ERROR",
                    message="Internal stream processing failed",
                    retryable=True,
                ),
            )
        return _TerminalState(
            content=content,
            usage=usage,
            error=StreamErrorData(
                code="CHATBOT_STREAM_ERROR",
                message="Internal stream processing failed",
                retryable=True,
            ),
        )

    def _refresh_short_term_memory(self, user_id: str, conversation_id: str) -> None:
        try:
            self.chat_service.refresh_short_term_memory(user_id, conversation_id)
        except Exception:
            return None


_CHAT_STREAM_SERVICE: ChatStreamService | None = None


def get_chat_stream_service() -> ChatStreamService:
    global _CHAT_STREAM_SERVICE
    if _CHAT_STREAM_SERVICE is None:
        _CHAT_STREAM_SERVICE = ChatStreamService()
    return _CHAT_STREAM_SERVICE
