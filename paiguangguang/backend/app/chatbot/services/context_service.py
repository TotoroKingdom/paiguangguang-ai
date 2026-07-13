from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Sequence

from sqlalchemy import desc, select
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.llm.prompt_builder import format_untrusted_context
from app.chatbot.llm.provider import LLMMessage
from app.chatbot.llm.token_estimator import ApproxTokenEstimator
from app.chatbot.memory.memory_retriever import SemanticMemoryRetriever
from app.chatbot.memory.semantic_memory import SemanticMemoryHit, SemanticMemoryIndex
from app.chatbot.memory.short_term_memory import ShortTermMemoryContext, ShortTermMemoryService
from app.chatbot.models.conversation import ChatbotConversation
from app.chatbot.models.message import ChatbotMessage
from app.chatbot.repositories.memory_repository import MemoryRecord, MemoryRepository
from app.core.config import Settings, get_settings
from app.db.session import build_session_factory


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class ContextSection:
    kind: str
    content: str
    source_ids: tuple[str, ...]
    priority: int
    trust_level: str
    token_estimate: int
    role: str
    order: int = 0
    clip_rank: int = 0


@dataclass(frozen=True, slots=True)
class ContextBundle:
    current_message: str
    sections: tuple[ContextSection, ...]
    token_budget: int
    token_estimate: int
    counts: dict[str, int]

    def history_messages(self) -> tuple[LLMMessage, ...]:
        return tuple(
            LLMMessage(role=section.role, content=section.content)
            for section in self.sections
            if section.kind != "current_user"
        )


class ContextService:
    def __init__(
        self,
        session_factory: sessionmaker[Session] | None = None,
        *,
        short_term_memory: ShortTermMemoryService | None = None,
        memory_repository: MemoryRepository | None = None,
        semantic_retriever: SemanticMemoryRetriever | None = None,
        token_estimator: ApproxTokenEstimator | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.session_factory = session_factory or build_session_factory(self.settings)
        self.short_term_memory = short_term_memory or ShortTermMemoryService(
            self.session_factory,
            settings=self.settings,
        )
        self.memory_repository = memory_repository or MemoryRepository(self.session_factory)
        if semantic_retriever is not None:
            self.semantic_retriever = semantic_retriever
        elif self.settings.chatbot_semantic_memory_enabled:
            semantic_index = SemanticMemoryIndex(settings=self.settings)
            self.semantic_retriever = SemanticMemoryRetriever(
                index=semantic_index,
                memory_repository=self.memory_repository,
                settings=self.settings,
            )
        else:
            self.semantic_retriever = None
        self.token_estimator = token_estimator or ApproxTokenEstimator()

    def build(
        self,
        user_id: str,
        conversation_id: str,
        current_message: str,
        *,
        before_sequence_number: int | None = None,
    ) -> ContextBundle:
        if not hasattr(self.short_term_memory, "load_context"):
            return self._build_legacy_bundle(
                user_id,
                conversation_id,
                current_message,
                before_sequence_number=before_sequence_number,
            )
        with self.session_factory() as session:
            short_term = self.short_term_memory.load_context(
                session,
                user_id,
                conversation_id,
                before_sequence_number=before_sequence_number,
            )
            before_sequence_number = self._before_sequence_number(short_term)
            recent_rows = self._recent_rows(session, user_id, conversation_id, before_sequence_number)
            summary_section = self._summary_section(short_term)
            recent_sections = self._recent_sections(recent_rows)
            long_term_sections, seen_memory_hashes = self._long_term_sections(user_id)
            semantic_sections = self._semantic_sections(user_id, current_message, seen_hashes=seen_memory_hashes)

        current_section = self._current_user_section(current_message)
        candidates = [
            current_section,
            *recent_sections,
            *(() if summary_section is None else (summary_section,)),
            *long_term_sections,
            *semantic_sections,
        ]
        selected = self._clip_to_budget(candidates)
        ordered = tuple(sorted(selected, key=lambda section: (-section.priority, section.order)))
        bundle = ContextBundle(
            current_message=current_message,
            sections=ordered,
            token_budget=self.settings.chatbot_context_token_budget,
            token_estimate=sum(section.token_estimate for section in ordered),
            counts=self._counts(ordered),
        )
        self._touch_memory_access(user_id, ordered)
        return bundle

    def _build_legacy_bundle(
        self,
        user_id: str,
        conversation_id: str,
        current_message: str,
        *,
        before_sequence_number: int | None = None,
    ) -> ContextBundle:
        with self.session_factory() as session:
            history = tuple(
                self.short_term_memory.load_history(  # type: ignore[attr-defined]
                    session,
                    user_id,
                    conversation_id,
                    before_sequence_number=before_sequence_number or 1,
                )
            )
        current_section = self._current_user_section(current_message)
        recent_sections = [
            ContextSection(
                kind="recent",
                content=message.content,
                source_ids=(),
                priority=90,
                trust_level="trusted",
                token_estimate=self.token_estimator.estimate_message(message.content),
                role=message.role,
                order=index,
                clip_rank=index,
            )
            for index, message in enumerate(history)
        ]
        sections = tuple([current_section, *recent_sections])
        return ContextBundle(
            current_message=current_message,
            sections=sections,
            token_budget=self.settings.chatbot_context_token_budget,
            token_estimate=sum(section.token_estimate for section in sections),
            counts=self._counts(sections),
        )

    def _before_sequence_number(self, short_term: ShortTermMemoryContext) -> int:
        before_sequence_number = short_term.state.get("before_sequence_number")
        if isinstance(before_sequence_number, int) and before_sequence_number > 0:
            return before_sequence_number
        return 1

    def _summary_section(self, short_term: ShortTermMemoryContext) -> ContextSection | None:
        summary_text = short_term.summary or ""
        if not summary_text.strip():
            return None
        source_ids = tuple(str(source_id) for source_id in short_term.state.get("source_message_ids", []) if str(source_id).strip())
        return ContextSection(
            kind="summary",
            content=summary_text,
            source_ids=source_ids,
            priority=80,
            trust_level="trusted",
            token_estimate=self.token_estimator.estimate_section(summary_text, source_count=len(source_ids)),
            role="assistant",
            order=0,
            clip_rank=0,
        )

    def _recent_rows(
        self,
        session: Session,
        user_id: str,
        conversation_id: str,
        before_sequence_number: int,
    ) -> list[ChatbotMessage]:
        limit = max(1, int(self.settings.chatbot_recent_message_limit))
        rows = list(
            session.scalars(
                select(ChatbotMessage)
                .where(
                    ChatbotMessage.conversation_id == conversation_id,
                    ChatbotMessage.user_id == user_id,
                    ChatbotMessage.sequence_number < before_sequence_number,
                    ChatbotMessage.status == "completed",
                    ChatbotMessage.role.in_(("user", "assistant")),
                )
                .order_by(desc(ChatbotMessage.sequence_number), desc(ChatbotMessage.id))
                .limit(limit)
            )
        )
        return list(reversed(rows))

    def _recent_sections(self, rows: Sequence[ChatbotMessage]) -> list[ContextSection]:
        sections: list[ContextSection] = []
        for order, row in enumerate(rows):
            sections.append(
                ContextSection(
                    kind="recent",
                    content=row.content,
                    source_ids=(str(row.id),),
                    priority=90,
                    trust_level="trusted",
                    token_estimate=self.token_estimator.estimate_message(row.content),
                    role=row.role,
                    order=order,
                    clip_rank=order,
                )
            )
        return sections

    def _long_term_sections(self, user_id: str) -> tuple[list[ContextSection], set[str]]:
        if not self.settings.chatbot_long_term_memory_enabled:
            return [], set()
        records = [
            record
            for record in self.memory_repository.list_owned(user_id, status="active")
            if record.confidence >= self.settings.chatbot_memory_min_confidence
            and (record.expires_at is None or record.expires_at > _utcnow())
        ]
        records.sort(key=lambda record: (record.updated_at, record.id), reverse=True)

        sections: list[ContextSection] = []
        seen_hashes: set[str] = set()
        for order, record in enumerate(records):
            if record.normalized_hash in seen_hashes:
                continue
            seen_hashes.add(record.normalized_hash)
            sections.append(self._memory_section(record, order=order, kind="long_term", priority=70, clip_rank=-order))
        return sections, seen_hashes

    def _semantic_sections(self, user_id: str, current_message: str, *, seen_hashes: set[str] | None = None) -> list[ContextSection]:
        if self.semantic_retriever is None:
            return []
        try:
            hits = self.semantic_retriever.search(
                user_id,
                current_message,
                top_k=self.settings.chatbot_semantic_top_k,
            )
        except Exception:
            return []

        sections: list[ContextSection] = []
        seen_hashes = set(seen_hashes or set())
        for order, hit in enumerate(hits):
            normalized_hash = hit.record.normalized_hash
            if normalized_hash in seen_hashes:
                continue
            seen_hashes.add(normalized_hash)
            sections.append(self._semantic_section(hit, order=order, clip_rank=-order))
        return sections

    def _current_user_section(self, current_message: str) -> ContextSection:
        return ContextSection(
            kind="current_user",
            content=current_message,
            source_ids=(),
            priority=100,
            trust_level="trusted",
            token_estimate=self.token_estimator.estimate_message(current_message),
            role="user",
            order=0,
            clip_rank=0,
        )

    def _memory_section(
        self,
        record: MemoryRecord,
        *,
        order: int,
        kind: str,
        priority: int,
        clip_rank: int,
    ) -> ContextSection:
        rendered = format_untrusted_context(
            kind=kind,
            source_ids=(record.id,),
            content=record.content,
        )
        return ContextSection(
            kind=kind,
            content=rendered,
            source_ids=(record.id,),
            priority=priority,
            trust_level="untrusted",
            token_estimate=self.token_estimator.estimate_section(rendered, source_count=1),
            role="assistant",
            order=order,
            clip_rank=clip_rank,
        )

    def _semantic_section(self, hit: SemanticMemoryHit, *, order: int, clip_rank: int) -> ContextSection:
        rendered = format_untrusted_context(
            kind="semantic",
            source_ids=(hit.memory_id,),
            content=hit.content,
        )
        return ContextSection(
            kind="semantic",
            content=rendered,
            source_ids=(hit.memory_id,),
            priority=60,
            trust_level="untrusted",
            token_estimate=self.token_estimator.estimate_section(rendered, source_count=1),
            role="assistant",
            order=order,
            clip_rank=clip_rank,
        )

    def _clip_to_budget(self, sections: Sequence[ContextSection]) -> list[ContextSection]:
        selected = list(sections)
        budget = max(1, int(self.settings.chatbot_context_token_budget))
        total = sum(section.token_estimate for section in selected)
        if total <= budget:
            return selected

        removable = [section for section in selected if section.kind != "current_user"]
        removable.sort(key=lambda section: (section.priority, section.clip_rank, section.order))

        while total > budget and removable:
            section = removable.pop(0)
            if section not in selected:
                continue
            selected.remove(section)
            total -= section.token_estimate
        return selected

    @staticmethod
    def _counts(sections: Sequence[ContextSection]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for section in sections:
            counts[section.kind] = counts.get(section.kind, 0) + 1
        return counts

    def _touch_memory_access(self, user_id: str, sections: Sequence[ContextSection]) -> None:
        touched: set[str] = set()
        now = _utcnow()
        for section in sections:
            if section.kind not in {"long_term", "semantic"}:
                continue
            memory_id = section.source_ids[0] if section.source_ids else None
            if memory_id is None or memory_id in touched:
                continue
            touched.add(memory_id)
            try:
                self.memory_repository.update(memory_id, user_id, last_accessed_at=now)
            except Exception:
                continue
