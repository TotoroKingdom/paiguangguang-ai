from datetime import datetime, timezone

from sqlalchemy import Select, desc, select
from sqlalchemy.orm import Session, selectinload

from app.models import Conversation, Message, uuid_string


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ConversationRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, owner_id: str, conversation_id: str, *, with_messages: bool = False) -> Conversation | None:
        query: Select[tuple[Conversation]] = select(Conversation).where(
            Conversation.owner_id == owner_id, Conversation.id == conversation_id
        )
        if with_messages:
            query = query.options(selectinload(Conversation.messages))
        return self.session.scalar(query)

    def list(self, owner_id: str, limit: int, cursor_time: datetime | None, cursor_id: str | None, query: str) -> list[Conversation]:
        statement = select(Conversation).where(Conversation.owner_id == owner_id)
        if query:
            statement = statement.where(Conversation.title.ilike(f"%{query}%"))
        if cursor_time is not None and cursor_id is not None:
            statement = statement.where(
                (Conversation.updated_at < cursor_time)
                | ((Conversation.updated_at == cursor_time) & (Conversation.id < cursor_id))
            )
        return list(
            self.session.scalars(
                statement.order_by(desc(Conversation.updated_at), desc(Conversation.id)).limit(limit)
            )
        )

    def create(
        self,
        owner_id: str,
        title: str = "新对话",
        migration_key: str | None = None,
        conversation_id: str | None = None,
    ) -> Conversation:
        now = utc_now()
        result = Conversation(
            id=conversation_id or uuid_string(),
            owner_id=owner_id,
            migration_key=migration_key,
            title=title,
            created_at=now,
            updated_at=now,
            version=1,
        )
        self.session.add(result)
        self.session.flush()
        return result

    def get_by_migration_key(self, owner_id: str, migration_key: str) -> Conversation | None:
        return self.session.scalar(
            select(Conversation).where(
                Conversation.owner_id == owner_id,
                Conversation.migration_key == migration_key,
            )
        )

    def next_seq(self, conversation_id: str) -> int:
        latest = self.session.scalar(
            select(Message.seq)
            .where(Message.conversation_id == conversation_id)
            .order_by(desc(Message.seq))
            .limit(1)
        )
        return (latest or 0) + 1

