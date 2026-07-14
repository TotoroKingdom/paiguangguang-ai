from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.memory.semantic_memory import SemanticMemoryIndex
from app.chatbot.memory.short_term_memory import ShortTermMemoryService
from app.chatbot.models.conversation import ChatbotConversation
from app.core.config import Settings, get_settings


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CleanupService:
    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        short_term_memory: ShortTermMemoryService,
        settings: Settings | None = None,
        semantic_index: SemanticMemoryIndex | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.short_term_memory = short_term_memory
        self.settings = settings or get_settings()
        self.semantic_index = semantic_index
        if self.semantic_index is None and self.settings.chatbot_semantic_memory_enabled:
            self.semantic_index = SemanticMemoryIndex(settings=self.settings)

    def cleanup_memory(self, payload: Mapping[str, object]) -> None:
        if self.semantic_index is not None and self.semantic_index.enabled:
            self.semantic_index.delete_memory(str(payload["memory_id"]))

    def cleanup_conversation(self, payload: Mapping[str, object]) -> None:
        user_id = str(payload["user_id"])
        conversation_id = str(payload["conversation_id"])
        self.short_term_memory.clear_conversation(user_id, conversation_id)
        if self.semantic_index is not None and self.semantic_index.enabled:
            memory_ids = payload.get("memory_ids", [])
            if isinstance(memory_ids, list):
                for memory_id in memory_ids:
                    self.semantic_index.delete_memory(str(memory_id))
        with self.session_factory() as session:
            session.execute(
                update(ChatbotConversation)
                .where(
                    ChatbotConversation.id == conversation_id,
                    ChatbotConversation.user_id == user_id,
                    ChatbotConversation.status == "deleted",
                )
                .values(cleanup_status="completed", updated_at=_utcnow())
            )
            session.commit()

    def mark_retry(self, payload: Mapping[str, object]) -> None:
        conversation_id = payload.get("conversation_id")
        if conversation_id is None:
            return
        user_id = str(payload["user_id"])
        with self.session_factory() as session:
            session.execute(
                update(ChatbotConversation)
                .where(
                    ChatbotConversation.id == str(conversation_id),
                    ChatbotConversation.user_id == user_id,
                    ChatbotConversation.status == "deleted",
                )
                .values(cleanup_status="retry", updated_at=_utcnow())
            )
            session.commit()
