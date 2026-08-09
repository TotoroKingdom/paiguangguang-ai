from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine

from app.core.config import get_settings
from app.core.config import Settings
from app.db.session import resolve_database_url


def get_alembic_config(settings: Settings | None = None) -> Config:
    backend_dir = Path(__file__).resolve().parents[2]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    database_url = resolve_database_url(settings or get_settings())
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    config.attributes["connection"] = create_engine(database_url, future=True, pool_pre_ping=True).connect()
    config.attributes["close_connection"] = True
    return config
