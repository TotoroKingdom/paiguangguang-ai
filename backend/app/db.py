from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
)


@event.listens_for(engine, "connect")
def configure_sqlite(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)


def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def init_db() -> None:
    # The container entrypoint runs Alembic; this fallback keeps local uvicorn usable.
    from app.models import Conversation, Message  # noqa: F401
    from app.modules.capabilities.models import (  # noqa: F401
        CapabilityDefinition,
        CapabilityDependency,
        CapabilityRun,
        CapabilityVersion,
    )
    from app.modules.identity.models import AdminSession, AdminUser  # noqa: F401
    from app.modules.personal.models import (  # noqa: F401
        McpConnection,
        McpServer,
        PersonalSkill,
        UserFile,
    )
    from app.modules.runtime.models import (  # noqa: F401
        AgentRun,
        RunMessage,
        RunSlot,
        RunStep,
        RunTrace,
    )
    from app.modules.observability.models import AuditEvent  # noqa: F401

    if settings.database_path:
        path = Path(settings.database_path)
        if str(path) not in {":memory:", ""}:
            path.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)

