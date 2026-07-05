from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings


def resolve_database_url(settings: Settings | None = None) -> str:
    resolved_settings = settings or get_settings()
    database_url = resolved_settings.test_database_url or resolved_settings.database_url
    if not database_url:
        raise ValueError("DATABASE_URL is not configured")
    return database_url


def build_engine(settings: Settings | None = None) -> Engine:
    database_url = resolve_database_url(settings)
    return create_engine(database_url, future=True, pool_pre_ping=True)


def build_session_factory(
    settings: Settings | None = None,
    engine: Engine | None = None,
) -> sessionmaker[Session]:
    resolved_engine = engine or build_engine(settings)
    return sessionmaker(bind=resolved_engine, autoflush=False, autocommit=False)


def get_db_session() -> Generator[Session, None, None]:
    session_factory = build_session_factory()
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
