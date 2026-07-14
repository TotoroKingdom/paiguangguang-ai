from __future__ import annotations

import re
from collections.abc import Mapping

from sqlalchemy import select, update
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.models.conversation import ChatbotConversation
from app.chatbot.models.message import ChatbotMessage
from app.chatbot.repositories.job_repository import JobRepository
from app.core.config import Settings, get_settings


class CompletionJobService:
    def __init__(self, repository: JobRepository, *, settings: Settings | None = None) -> None:
        self.repository = repository
        self.settings = settings or get_settings()

    def enqueue_completed_turn(
        self,
        session: Session,
        *,
        user_id: str,
        conversation_id: str,
        user_message_id: str,
        assistant_message_id: str,
    ) -> None:
        payload = {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "user_message_id": user_message_id,
            "assistant_message_id": assistant_message_id,
        }
        if self.settings.chatbot_long_term_memory_enabled:
            self.repository.enqueue(
                session,
                kind="completed_turn_memory",
                dedup_key=f"completed-turn-memory:{user_message_id}",
                payload=payload,
            )
        self.repository.enqueue(
            session,
            kind="refresh_conversation_context",
            dedup_key=f"refresh-conversation-context:{assistant_message_id}",
            payload=payload,
        )
        self.repository.enqueue(
            session,
            kind="auto_title",
            dedup_key=f"auto-title:{conversation_id}",
            payload=payload,
        )


class ConversationTitleService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    @staticmethod
    def derive_title(content: str) -> str:
        normalized = re.sub(r"\s+", " ", content).strip()
        return normalized[:60] or "新对话"

    def apply_auto_title(self, payload: Mapping[str, object]) -> bool:
        conversation_id = str(payload["conversation_id"])
        user_id = str(payload["user_id"])
        user_message_id = str(payload["user_message_id"])
        with self.session_factory() as session:
            message = session.scalar(
                select(ChatbotMessage).where(
                    ChatbotMessage.id == user_message_id,
                    ChatbotMessage.user_id == user_id,
                    ChatbotMessage.conversation_id == conversation_id,
                    ChatbotMessage.role == "user",
                    ChatbotMessage.status == "completed",
                )
            )
            if message is None:
                return False
            result = session.execute(
                update(ChatbotConversation)
                .where(
                    ChatbotConversation.id == conversation_id,
                    ChatbotConversation.user_id == user_id,
                    ChatbotConversation.title_source == "default",
                    ChatbotConversation.deleted_at.is_(None),
                )
                .values(title=self.derive_title(message.content), title_source="auto")
            )
            session.commit()
            return bool(result.rowcount)
