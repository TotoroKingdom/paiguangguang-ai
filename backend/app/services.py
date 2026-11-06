import base64
import json
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Conversation, Message
from app.repositories import ConversationRepository, utc_now
from app.schemas import (
    AttachmentSnapshot,
    ConversationResponse,
    ConversationSummary,
    ExecutionStep,
    MessagePatch,
    MessageRequest,
    MessageResponse,
    TurnCreate,
    TurnResponse,
)


def dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def loads(value: str, default):
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def summary(conversation: Conversation) -> ConversationSummary:
    return ConversationSummary(
        id=conversation.id,
        title=conversation.title,
        createdAt=conversation.created_at.replace(tzinfo=timezone.utc),
        updatedAt=conversation.updated_at.replace(tzinfo=timezone.utc),
        version=conversation.version,
    )


def message_response(message: Message) -> MessageResponse:
    return MessageResponse(
        id=message.id,
        role=message.role,
        content=message.content,
        status=message.status,
        steps=loads(message.steps_json, []),
        capability=loads(message.capability_json, None),
        attachments=loads(message.attachments_json, []),
        request=loads(message.request_json, None),
        clientTurnId=message.client_turn_id,
        createdAt=message.created_at.replace(tzinfo=timezone.utc),
        updatedAt=message.updated_at.replace(tzinfo=timezone.utc),
    )


class ConversationService:
    def __init__(self, session: Session):
        self.session = session
        self.repository = ConversationRepository(session)

    def get_owned(self, owner_id: str, conversation_id: str, *, with_messages: bool = False) -> Conversation:
        conversation = self.repository.get(owner_id, conversation_id, with_messages=with_messages)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conversation

    def recover_orphaned_generating(self, conversation: Conversation) -> None:
        changed = False
        for message in conversation.messages:
            if message.role == "assistant" and message.status == "generating":
                message.status = "stopped"
                message.updated_at = utc_now()
                changed = True
        if changed:
            conversation.updated_at = utc_now()
            conversation.version += 1
            self.session.commit()

    def detail(self, owner_id: str, conversation_id: str) -> ConversationResponse:
        conversation = self.get_owned(owner_id, conversation_id, with_messages=True)
        self.recover_orphaned_generating(conversation)
        return ConversationResponse(
            **summary(conversation).model_dump(),
            messages=[message_response(item) for item in conversation.messages],
        )

    def create(
        self,
        owner_id: str,
        title: str = "新对话",
        migration_key: str | None = None,
        conversation_id: str | None = None,
    ) -> ConversationSummary:
        if migration_key:
            existing = self.repository.get_by_migration_key(owner_id, migration_key)
            if existing is not None:
                return summary(existing)
        conversation = self.repository.create(owner_id, title, migration_key, conversation_id)
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            if migration_key:
                existing = self.repository.get_by_migration_key(owner_id, migration_key)
                if existing is not None:
                    return summary(existing)
            raise
        return summary(conversation)

    def rename(self, owner_id: str, conversation_id: str, title: str, version: int) -> ConversationSummary:
        now = utc_now()
        result = self.session.execute(
            update(Conversation)
            .where(
                Conversation.owner_id == owner_id,
                Conversation.id == conversation_id,
                Conversation.version == version,
            )
            .values(title=title, updated_at=now, version=Conversation.version + 1)
        )
        if result.rowcount != 1:
            conversation = self.get_owned(owner_id, conversation_id)
            raise HTTPException(
                status_code=409,
                detail="Conversation version conflict"
                if conversation.version != version
                else "Conversation update conflict",
            )
        conversation = self.get_owned(owner_id, conversation_id)
        self.session.commit()
        return summary(conversation)

    def delete(self, owner_id: str, conversation_id: str) -> None:
        conversation = self.get_owned(owner_id, conversation_id)
        self.session.delete(conversation)
        self.session.commit()

    def create_turn(self, owner_id: str, conversation_id: str, request: TurnCreate) -> TurnResponse:
        conversation = self.get_owned(owner_id, conversation_id, with_messages=True)
        if request.request.conversationId not in {None, conversation_id}:
            raise HTTPException(status_code=422, detail="Request conversation does not match path")
        if request.request.text != request.text:
            raise HTTPException(status_code=422, detail="Request text does not match message text")
        existing = self.session.scalar(
            select(Message).where(
                Message.conversation_id == conversation_id,
                Message.client_turn_id == request.clientTurnId,
                Message.role == "user",
            )
        )
        if existing is not None:
            assistant = self.session.scalar(
                select(Message).where(
                    Message.conversation_id == conversation_id,
                    Message.seq == existing.seq + 1,
                    Message.role == "assistant",
                )
            )
            if assistant is None:
                raise HTTPException(status_code=409, detail="Existing turn is incomplete")
            return TurnResponse(
                conversation=summary(conversation),
                userMessage=message_response(existing),
                assistantMessage=message_response(assistant),
            )
        seq = self.repository.next_seq(conversation_id)
        now = utc_now()
        user_message = Message(
            conversation_id=conversation_id,
            seq=seq,
            client_turn_id=request.clientTurnId,
            role="user",
            content=request.text,
            status="complete",
            steps_json="[]",
            capability_json=dumps(request.capability.model_dump() if request.capability else None),
            attachments_json=dumps([item.model_dump() for item in request.attachments]),
            request_json=dumps(request.request.model_dump(by_alias=True)),
            created_at=now,
            updated_at=now,
        )
        assistant_message = Message(
            conversation_id=conversation_id,
            seq=seq + 1,
            role="assistant",
            content="",
            status="generating",
            steps_json="[]",
            capability_json="null",
            attachments_json="[]",
            request_json=dumps(request.request.model_dump(by_alias=True)),
            created_at=now,
            updated_at=now,
        )
        conversation.messages.extend([user_message, assistant_message])
        if conversation.version == 1 and conversation.migration_key is None:
            conversation.title = request.text.strip()[:24]
        conversation.updated_at = now
        conversation.version += 1
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            existing = self.session.scalar(
                select(Message).where(
                    Message.conversation_id == conversation_id,
                    Message.client_turn_id == request.clientTurnId,
                    Message.role == "user",
                )
            )
            if existing is None:
                raise
            assistant = self.session.scalar(
                select(Message).where(
                    Message.conversation_id == conversation_id,
                    Message.seq == existing.seq + 1,
                    Message.role == "assistant",
                )
            )
            if assistant is None:
                raise HTTPException(status_code=409, detail="Existing turn is incomplete")
            return TurnResponse(
                conversation=summary(conversation),
                userMessage=message_response(existing),
                assistantMessage=message_response(assistant),
            )
        return TurnResponse(
            conversation=summary(conversation),
            userMessage=message_response(user_message),
            assistantMessage=message_response(assistant_message),
        )

    def patch_message(
        self, owner_id: str, conversation_id: str, message_id: str, patch: MessagePatch
    ) -> MessageResponse:
        conversation = self.get_owned(owner_id, conversation_id, with_messages=True)
        message = next((item for item in conversation.messages if item.id == message_id), None)
        if message is None or message.role != "assistant":
            raise HTTPException(status_code=404, detail="Message not found")
        allowed = {
            "generating": {"generating", "complete", "stopped", "error"},
            "complete": {"complete"},
            "stopped": {"stopped", "generating", "complete", "error"},
            "error": {"error", "generating"},
        }
        if patch.status not in allowed.get(message.status, set()):
            raise HTTPException(status_code=409, detail="Invalid message status transition")
        message.content = patch.content
        message.status = patch.status
        message.steps_json = dumps([item.model_dump() for item in patch.steps])
        if patch.request is not None:
            message.request_json = dumps(patch.request.model_dump(by_alias=True))
        message.updated_at = utc_now()
        conversation.updated_at = message.updated_at
        self.session.commit()
        return message_response(message)


def encode_cursor(conversation: Conversation) -> str:
    value = f"{conversation.updated_at.isoformat()}|{conversation.id}".encode("utf-8")
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def decode_cursor(value: str) -> tuple[datetime, str]:
    try:
        padded = value + "=" * (-len(value) % 4)
        raw = base64.urlsafe_b64decode(padded).decode("utf-8")
        timestamp, conversation_id = raw.split("|", 1)
        return datetime.fromisoformat(timestamp), conversation_id
    except (ValueError, UnicodeDecodeError) as error:
        raise HTTPException(status_code=400, detail="Invalid cursor") from error

