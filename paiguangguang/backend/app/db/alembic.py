from __future__ import annotations

from pathlib import Path

from alembic.config import Config

from app.core.config import get_settings
from app.db.session import resolve_database_url


def get_alembic_config() -> Config:
    backend_dir = Path(__file__).resolve().parents[2]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    config.set_main_option("sqlalchemy.url", resolve_database_url(get_settings()))
    return config
